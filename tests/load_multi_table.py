#!/usr/bin/env python3
"""
Load Test: Multiple Tables Mixed Workload

Creates 5 tables, each with 20 users, then runs a mixed workload of updates and reads.
"""

import asyncio
import aiohttp
import os
import sys
import time
import uuid
import random
from typing import List, Tuple, Optional
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn


class MultiTableLoadTest:
    """Load test for multiple tables with mixed workload"""
    
    def __init__(self, api_base_url: str):
        self.api_base_url = api_base_url.rstrip('/')
        self.table_count = 5
        self.users_per_table = 20
        self.console = Console()
        self.errors = []
        self.table_ids = []
        
    def log_error(self, message: str):
        """Log error message"""
        self.errors.append(message)
        self.console.print(f"❌ {message}", style="red")
        
    async def create_table(self, session: aiohttp.ClientSession, table_index: int) -> Tuple[bool, str]:
        """Create a test table and return (success, table_id)"""
        table_id = f"load-test-multi-{table_index}-{uuid.uuid4().hex[:8]}"
        payload = {
            'tableId': table_id,
            'displayName': f'Load Test Multi Table {table_index}'
        }
        
        try:
            async with session.post(
                f"{self.api_base_url}/tables",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 201:
                    return True, table_id
                elif response.status == 409:
                    # Table already exists, that's ok
                    return True, table_id
                else:
                    text = await response.text()
                    self.log_error(f"Failed to create table {table_id}. Status: {response.status}, Response: {text}")
                    return False, table_id
        except Exception as e:
            self.log_error(f"Exception creating table {table_id}: {str(e)}")
            return False, table_id
            
    async def create_user(self, session: aiohttp.ClientSession, table_id: str, user_index: int) -> Tuple[bool, float]:
        """Create a user in a specific table and return (success, latency_ms)"""
        username = f"user-{user_index:03d}"
        payload = {
            'submissionCount': user_index + 1,
            'totalCount': (user_index + 1) * 2
        }
        
        start_time = time.time()
        try:
            async with session.put(
                f"{self.api_base_url}/tables/{table_id}/users/{username}",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                latency = (time.time() - start_time) * 1000  # Convert to ms
                
                if response.status == 200:
                    return True, latency
                else:
                    text = await response.text()
                    self.log_error(f"Failed to create user {username} in table {table_id}. Status: {response.status}, Response: {text}")
                    return False, latency
                    
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            self.log_error(f"Exception creating user {username} in table {table_id}: {str(e)}")
            return False, latency
            
    async def read_user(self, session: aiohttp.ClientSession, table_id: str, user_index: int) -> Tuple[bool, float]:
        """Read a user from a specific table and return (success, latency_ms)"""
        username = f"user-{user_index:03d}"
        
        start_time = time.time()
        try:
            async with session.get(
                f"{self.api_base_url}/tables/{table_id}/users/{username}",
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                latency = (time.time() - start_time) * 1000  # Convert to ms
                
                if response.status == 200:
                    return True, latency
                else:
                    text = await response.text()
                    self.log_error(f"Failed to read user {username} from table {table_id}. Status: {response.status}, Response: {text}")
                    return False, latency
                    
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            self.log_error(f"Exception reading user {username} from table {table_id}: {str(e)}")
            return False, latency
            
    async def update_user(self, session: aiohttp.ClientSession, table_id: str, user_index: int) -> Tuple[bool, float]:
        """Update a user in a specific table and return (success, latency_ms)"""
        username = f"user-{user_index:03d}"
        # Generate new random scores for update
        payload = {
            'submissionCount': random.randint(1, 50),
            'totalCount': random.randint(51, 100)
        }
        
        start_time = time.time()
        try:
            async with session.put(
                f"{self.api_base_url}/tables/{table_id}/users/{username}",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                latency = (time.time() - start_time) * 1000  # Convert to ms
                
                if response.status == 200:
                    return True, latency
                else:
                    text = await response.text()
                    self.log_error(f"Failed to update user {username} in table {table_id}. Status: {response.status}, Response: {text}")
                    return False, latency
                    
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            self.log_error(f"Exception updating user {username} in table {table_id}: {str(e)}")
            return False, latency
            
    async def mixed_workload_operation(self, session: aiohttp.ClientSession) -> Tuple[str, bool, float]:
        """Perform a random mixed workload operation (read or update)"""
        # Choose random table and user
        table_id = random.choice(self.table_ids)
        user_index = random.randint(0, self.users_per_table - 1)
        
        # Choose operation type (70% reads, 30% updates for realistic workload)
        if random.random() < 0.7:
            operation = "read"
            success, latency = await self.read_user(session, table_id, user_index)
        else:
            operation = "update"
            success, latency = await self.update_user(session, table_id, user_index)
            
        return operation, success, latency
        
    def print_latency_summary(self, operation: str, latencies: List[float]):
        """Print latency statistics"""
        if not latencies:
            return
            
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
        """Run the complete multi-table load test"""
        self.console.print(f"🚀 Starting Multi-Table Load Test", style="bold blue")
        self.console.print(f"📊 Target: {self.table_count} tables × {self.users_per_table} users = {self.table_count * self.users_per_table} total users")
        self.console.print(f"🔗 API Base URL: {self.api_base_url}")
        
        async with aiohttp.ClientSession() as session:
            # Phase 1: Create tables
            self.console.print(f"\n📦 Phase 1: Creating {self.table_count} tables...")
            
            table_tasks = [
                self.create_table(session, i) 
                for i in range(self.table_count)
            ]
            table_results = await asyncio.gather(*table_tasks, return_exceptions=True)
            
            successful_tables = 0
            for result in table_results:
                if isinstance(result, tuple):
                    success, table_id = result
                    if success:
                        self.table_ids.append(table_id)
                        successful_tables += 1
                        
            self.console.print(f"✅ Created {successful_tables}/{self.table_count} tables")
            
            if not self.table_ids:
                self.log_error("No tables were created successfully")
                return False
                
            # Phase 2: Populate tables with users
            self.console.print(f"\n👥 Phase 2: Populating tables with users...")
            
            create_latencies = []
            user_tasks = []
            
            for table_id in self.table_ids:
                for user_index in range(self.users_per_table):
                    user_tasks.append(self.create_user(session, table_id, user_index))
                    
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
                transient=True
            ) as progress:
                task = progress.add_task("Creating users...", total=None)
                user_results = await asyncio.gather(*user_tasks, return_exceptions=True)
                
            successful_creates = 0
            for result in user_results:
                if isinstance(result, tuple):
                    success, latency = result
                    create_latencies.append(latency)
                    if success:
                        successful_creates += 1
                        
            self.console.print(f"✅ Created {successful_creates}/{len(user_tasks)} users across all tables")
            
            # Phase 3: Mixed workload operations
            self.console.print(f"\n⚡ Phase 3: Running mixed workload operations...")
            
            # Run 200 mixed operations (reads and updates)
            mixed_operations = 200
            read_latencies = []
            update_latencies = []
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
                transient=True
            ) as progress:
                task = progress.add_task("Running mixed workload...", total=None)
                
                mixed_tasks = [
                    self.mixed_workload_operation(session) 
                    for _ in range(mixed_operations)
                ]
                
                mixed_results = await asyncio.gather(*mixed_tasks, return_exceptions=True)
                
            successful_reads = 0
            successful_updates = 0
            
            for result in mixed_results:
                if isinstance(result, tuple):
                    operation, success, latency = result
                    if operation == "read":
                        read_latencies.append(latency)
                        if success:
                            successful_reads += 1
                    else:  # update
                        update_latencies.append(latency)
                        if success:
                            successful_updates += 1
                            
            self.console.print(f"✅ Mixed workload: {successful_reads} successful reads, {successful_updates} successful updates")
            
        # Print results
        self.console.print(f"\n📈 Performance Results:", style="bold")
        self.print_latency_summary("Initial User Creation", create_latencies)
        self.print_latency_summary("Read Operations", read_latencies)
        self.print_latency_summary("Update Operations", update_latencies)
        
        # Final status
        if self.errors:
            self.console.print(f"\n❌ Test completed with {len(self.errors)} error(s):", style="red")
            for error in self.errors:
                self.console.print(f"   • {error}", style="red")
            return False
        else:
            self.console.print(f"\n✅ All operations completed successfully!", style="green")
            return True


def get_api_base_url() -> str:
    """Get API base URL from environment variable"""
    api_url = os.getenv('API_BASE_URL')
    if not api_url:
        print("❌ API_BASE_URL environment variable is required")
        print("Usage: export API_BASE_URL=https://your-api.com && python tests/load_multi_table.py")
        sys.exit(1)
        
    if not api_url.startswith(('http://', 'https://')):
        print(f"❌ Invalid API URL format: {api_url}")
        sys.exit(1)
        
    return api_url


async def main():
    """Main function"""
    api_base_url = get_api_base_url()
    
    # Run load test
    test = MultiTableLoadTest(api_base_url)
    success = await test.run_load_test()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())