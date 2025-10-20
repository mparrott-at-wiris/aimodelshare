#!/usr/bin/env python3
"""
Load Test: Mixed Duration Workload

Creates one table with 100 users and runs a configurable duration mixed read/write workload
with concurrent workers. Default 60s duration, configurable via LOAD_DURATION_SECONDS env var.
For CI: defaults to 20s and uses 30 concurrent workers instead of 50 for stability.
"""

import asyncio
import aiohttp
import os
import sys
import time
import uuid
import random
from typing import List, Tuple, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.live import Live


class MixedDurationLoadTest:
    """Load test with time-based mixed workload"""
    
    def __init__(self, api_base_url: str):
        self.api_base_url = api_base_url.rstrip('/')
        self.table_id = f"load-test-duration-{uuid.uuid4().hex[:8]}"
        self.user_count = 100
        
        # Get duration from environment variable or use default
        self.duration_seconds = int(os.getenv('LOAD_DURATION_SECONDS', 20))  # Default 20s for CI
        # Reduce concurrency for CI stability vs production (30 vs 50)
        self.concurrent_workers = 30
        
        self.console = Console()
        self.errors = []
        self.is_running = False
        self.stats = {
            'reads': {'count': 0, 'latencies': [], 'errors': 0},
            'updates': {'count': 0, 'latencies': [], 'errors': 0},
            'start_time': None,
            'end_time': None
        }
        
    def log_error(self, message: str):
        """Log error message"""
        self.errors.append(message)
        # Don't print errors during workload to avoid cluttering output
        
    async def create_table(self, session: aiohttp.ClientSession) -> bool:
        """Create the test table"""
        payload = {
            'tableId': self.table_id,
            'displayName': f'Load Test Duration Table {self.table_id}'
        }
        
        try:
            async with session.post(
                f"{self.api_base_url}/tables",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 201:
                    return True
                elif response.status == 409:
                    # Table already exists, that's ok
                    return True
                else:
                    text = await response.text()
                    self.log_error(f"Failed to create table. Status: {response.status}, Response: {text}")
                    return False
        except Exception as e:
            self.log_error(f"Exception creating table: {str(e)}")
            return False
            
    async def create_user(self, session: aiohttp.ClientSession, user_index: int) -> bool:
        """Create a single user"""
        username = f"duration-user-{user_index:03d}"
        payload = {
            'submissionCount': user_index + 1,
            'totalCount': (user_index + 1) * 2
        }
        
        try:
            async with session.put(
                f"{self.api_base_url}/tables/{self.table_id}/users/{username}",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                return response.status == 200
        except Exception:
            return False
            
    async def read_user(self, session: aiohttp.ClientSession, user_index: int) -> Tuple[bool, float]:
        """Read a random user and return (success, latency_ms)"""
        username = f"duration-user-{user_index:03d}"
        
        start_time = time.time()
        try:
            async with session.get(
                f"{self.api_base_url}/tables/{self.table_id}/users/{username}",
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                latency = (time.time() - start_time) * 1000
                return response.status == 200, latency
        except Exception:
            latency = (time.time() - start_time) * 1000
            return False, latency
            
    async def update_user(self, session: aiohttp.ClientSession, user_index: int) -> Tuple[bool, float]:
        """Update a random user and return (success, latency_ms)"""
        username = f"duration-user-{user_index:03d}"
        payload = {
            'submissionCount': random.randint(1, 100),
            'totalCount': random.randint(101, 200)
        }
        
        start_time = time.time()
        try:
            async with session.put(
                f"{self.api_base_url}/tables/{self.table_id}/users/{username}",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                latency = (time.time() - start_time) * 1000
                return response.status == 200, latency
        except Exception:
            latency = (time.time() - start_time) * 1000
            return False, latency
            
    async def worker_loop(self, session: aiohttp.ClientSession, worker_id: int):
        """Individual worker that performs operations during the test duration"""
        while self.is_running:
            # Choose random user
            user_index = random.randint(0, self.user_count - 1)
            
            # Choose operation type (70% reads, 30% updates)
            if random.random() < 0.7:
                operation = "reads"
                success, latency = await self.read_user(session, user_index)
            else:
                operation = "updates"
                success, latency = await self.update_user(session, user_index)
                
            # Update stats
            self.stats[operation]['count'] += 1
            self.stats[operation]['latencies'].append(latency)
            if not success:
                self.stats[operation]['errors'] += 1
                
            # Small delay to avoid overwhelming the API
            await asyncio.sleep(0.01)  # 10ms delay between operations per worker
            
    def create_stats_table(self) -> Table:
        """Create a real-time statistics table"""
        table = Table(title="Load Test Statistics (Real-time)")
        table.add_column("Metric", justify="right", style="cyan")
        table.add_column("Reads", justify="right", style="green")
        table.add_column("Updates", justify="right", style="yellow")
        table.add_column("Total", justify="right", style="magenta")
        
        read_count = self.stats['reads']['count']
        update_count = self.stats['updates']['count']
        total_count = read_count + update_count
        
        read_errors = self.stats['reads']['errors']
        update_errors = self.stats['updates']['errors']
        total_errors = read_errors + update_errors
        
        # Calculate averages
        read_avg = sum(self.stats['reads']['latencies']) / max(1, len(self.stats['reads']['latencies']))
        update_avg = sum(self.stats['updates']['latencies']) / max(1, len(self.stats['updates']['latencies']))
        
        # Calculate rates (operations per second)
        elapsed = time.time() - self.stats['start_time'] if self.stats['start_time'] else 1
        read_rate = read_count / elapsed
        update_rate = update_count / elapsed
        total_rate = total_count / elapsed
        
        table.add_row("Operations", str(read_count), str(update_count), str(total_count))
        table.add_row("Errors", str(read_errors), str(update_errors), str(total_errors))
        table.add_row("Avg Latency (ms)", f"{read_avg:.1f}", f"{update_avg:.1f}", "-")
        table.add_row("Rate (ops/sec)", f"{read_rate:.1f}", f"{update_rate:.1f}", f"{total_rate:.1f}")
        
        return table
        
    def print_final_summary(self):
        """Print final test summary"""
        read_latencies = self.stats['reads']['latencies']
        update_latencies = self.stats['updates']['latencies']
        
        self.console.print(f"\n📈 Final Performance Results:", style="bold")
        
        # Overall stats
        total_ops = self.stats['reads']['count'] + self.stats['updates']['count']
        total_errors = self.stats['reads']['errors'] + self.stats['updates']['errors']
        actual_duration = self.stats['end_time'] - self.stats['start_time']
        
        overall_table = Table(title="Overall Test Summary")
        overall_table.add_column("Metric", justify="right", style="cyan")
        overall_table.add_column("Value", justify="right", style="magenta")
        
        overall_table.add_row("Test Duration", f"{actual_duration:.1f}s")
        overall_table.add_row("Total Operations", str(total_ops))
        overall_table.add_row("Total Errors", str(total_errors))
        overall_table.add_row("Error Rate", f"{(total_errors / max(1, total_ops)) * 100:.2f}%")
        overall_table.add_row("Average Rate", f"{total_ops / actual_duration:.1f} ops/sec")
        
        self.console.print(overall_table)
        
        # Detailed latency stats
        if read_latencies:
            self.print_latency_summary("Read Operations", read_latencies)
        if update_latencies:
            self.print_latency_summary("Update Operations", update_latencies)
            
    def print_latency_summary(self, operation: str, latencies: List[float]):
        """Print latency statistics"""
        latencies.sort()
        count = len(latencies)
        
        table = Table(title=f"{operation} Latency Summary")
        table.add_column("Metric", justify="right", style="cyan")
        table.add_column("Value (ms)", justify="right", style="magenta")
        
        table.add_row("Count", str(count))
        table.add_row("Min", f"{min(latencies):.1f}")
        table.add_row("Max", f"{max(latencies):.1f}")
        table.add_row("Mean", f"{sum(latencies) / count:.1f}")
        table.add_row("Median", f"{latencies[count // 2]:.1f}")
        table.add_row("P95", f"{latencies[max(0, min(count-1, int(count * 0.95)))]:.1f}")
        table.add_row("P99", f"{latencies[max(0, min(count-1, int(count * 0.99)))]:.1f}")
        
        self.console.print(table)
        
    async def run_load_test(self) -> bool:
        """Run the complete duration-based load test"""
        self.console.print(f"🚀 Starting Mixed Duration Load Test", style="bold blue")
        self.console.print(f"⏱️  Duration: {self.duration_seconds} seconds")
        self.console.print(f"👥 Users: {self.user_count}")
        self.console.print(f"⚡ Concurrent Workers: {self.concurrent_workers}")
        self.console.print(f"🔗 API Base URL: {self.api_base_url}")
        self.console.print(f"🧪 Table ID: {self.table_id}")
        
        async with aiohttp.ClientSession() as session:
            # Phase 1: Create table and users
            self.console.print(f"\n📦 Phase 1: Setup (table + {self.user_count} users)...")
            
            if not await self.create_table(session):
                return False
                
            # Create users in parallel batches to avoid overwhelming the API
            batch_size = 20
            successful_creates = 0
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                console=self.console,
                transient=True
            ) as progress:
                task = progress.add_task("Creating users...", total=self.user_count)
                
                for i in range(0, self.user_count, batch_size):
                    batch_end = min(i + batch_size, self.user_count)
                    batch_tasks = [
                        self.create_user(session, j) 
                        for j in range(i, batch_end)
                    ]
                    
                    results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                    successful_creates += sum(1 for r in results if r is True)
                    
                    progress.update(task, advance=len(batch_tasks))
                    
            self.console.print(f"✅ Created {successful_creates}/{self.user_count} users")
            
            # Phase 2: Duration-based mixed workload
            self.console.print(f"\n⚡ Phase 2: Running {self.duration_seconds}s mixed workload with {self.concurrent_workers} workers...")
            
            # Start workers
            self.is_running = True
            self.stats['start_time'] = time.time()
            
            worker_tasks = [
                self.worker_loop(session, i) 
                for i in range(self.concurrent_workers)
            ]
            
            # Create progress bar for duration
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=self.console,
                refresh_per_second=2
            ) as progress:
                duration_task = progress.add_task("Running workload...", total=self.duration_seconds)
                
                # Run for the specified duration
                start_time = time.time()
                
                while time.time() - start_time < self.duration_seconds:
                    await asyncio.sleep(0.5)
                    elapsed = time.time() - start_time
                    progress.update(duration_task, completed=min(elapsed, self.duration_seconds))
                    
            # Stop workers
            self.is_running = False
            self.stats['end_time'] = time.time()
            
            # Wait for workers to finish current operations
            await asyncio.gather(*worker_tasks, return_exceptions=True)
            
        # Print results
        self.print_final_summary()
        
        # Final status
        total_errors = self.stats['reads']['errors'] + self.stats['updates']['errors']
        if total_errors > 0:
            self.console.print(f"\n⚠️  Test completed with {total_errors} error(s)", style="yellow")
            # For this test, we don't fail on errors unless error rate is very high (>10%)
            total_ops = self.stats['reads']['count'] + self.stats['updates']['count']
            error_rate = total_errors / max(1, total_ops)
            if error_rate > 0.1:  # More than 10% error rate
                self.console.print(f"❌ Error rate too high: {error_rate * 100:.1f}%", style="red")
                return False
            else:
                self.console.print(f"✅ Error rate acceptable: {error_rate * 100:.2f}%", style="green")
                return True
        else:
            self.console.print(f"\n✅ Test completed successfully with no errors!", style="green")
            return True


def get_api_base_url() -> str:
    """Get API base URL from environment variable"""
    api_url = os.getenv('API_BASE_URL')
    if not api_url:
        print("❌ API_BASE_URL environment variable is required")
        print("Usage: export API_BASE_URL=https://your-api.com && python tests/load_mixed_duration.py")
        print("Optional: export LOAD_DURATION_SECONDS=30 (default: 20)")
        sys.exit(1)
        
    if not api_url.startswith(('http://', 'https://')):
        print(f"❌ Invalid API URL format: {api_url}")
        sys.exit(1)
        
    return api_url


async def main():
    """Main function"""
    api_base_url = get_api_base_url()
    
    # Show configuration
    duration = int(os.getenv('LOAD_DURATION_SECONDS', 20))
    console = Console()
    console.print(f"🔧 Configuration:", style="bold")
    console.print(f"   Duration: {duration} seconds")
    console.print(f"   API URL: {api_base_url}")
    
    # Run load test
    test = MixedDurationLoadTest(api_base_url)
    success = await test.run_load_test()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())