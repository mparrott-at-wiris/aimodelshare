#!/usr/bin/env python3
"""
Load Test: Single Table Concurrent Users

Creates one table and concurrently creates 100 distinct users, then reads them.
Prints latency summary and warns if userCount mismatch.
"""

import asyncio
import aiohttp
import os
import sys
import time
import uuid
from typing import List, Tuple, Optional
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn


class SingleTableLoadTest:
    """Load test for single table with concurrent user operations"""
    
    def __init__(self, api_base_url: str):
        self.api_base_url = api_base_url.rstrip('/')
        self.table_id = f"load-test-single-{uuid.uuid4().hex[:8]}"
        self.user_count = 100
        self.console = Console()
        self.errors = []
        self.latencies = []
        
    def log_error(self, message: str):
        """Log error message"""
        self.errors.append(message)
        self.console.print(f"❌ {message}", style="red")
        
    async def create_table(self, session: aiohttp.ClientSession) -> bool:
        """Create the test table"""
        payload = {
            'tableId': self.table_id,
            'displayName': f'Load Test Single Table {self.table_id}'
        }
        
        try:
            async with session.post(
                f"{self.api_base_url}/tables",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 201:
                    self.console.print(f"✅ Created table: {self.table_id}", style="green")
                    return True
                elif response.status == 409:
                    # Table already exists, that's ok
                    self.console.print(f"✅ Table already exists: {self.table_id}", style="yellow")
                    return True
                else:
                    text = await response.text()
                    self.log_error(f"Failed to create table. Status: {response.status}, Response: {text}")
                    return False
        except Exception as e:
            self.log_error(f"Exception creating table: {str(e)}")
            return False
            
    async def create_user(self, session: aiohttp.ClientSession, user_index: int) -> Tuple[bool, float]:
        """Create a single user and return (success, latency_ms)"""
        username = f"loadtest-user-{user_index:03d}"
        payload = {
            'submissionCount': user_index * 2,
            'totalCount': user_index * 3
        }
        
        start_time = time.time()
        try:
            async with session.put(
                f"{self.api_base_url}/tables/{self.table_id}/users/{username}",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                latency = (time.time() - start_time) * 1000  # Convert to ms
                
                if response.status == 200:
                    return True, latency
                else:
                    text = await response.text()
                    self.log_error(f"Failed to create user {username}. Status: {response.status}, Response: {text}")
                    return False, latency
                    
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            self.log_error(f"Exception creating user {username}: {str(e)}")
            return False, latency
            
    async def read_user(self, session: aiohttp.ClientSession, user_index: int) -> Tuple[bool, float]:
        """Read a single user and return (success, latency_ms)"""
        username = f"loadtest-user-{user_index:03d}"
        
        start_time = time.time()
        try:
            async with session.get(
                f"{self.api_base_url}/tables/{self.table_id}/users/{username}",
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                latency = (time.time() - start_time) * 1000  # Convert to ms
                
                if response.status == 200:
                    return True, latency
                else:
                    text = await response.text()
                    self.log_error(f"Failed to read user {username}. Status: {response.status}, Response: {text}")
                    return False, latency
                    
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            self.log_error(f"Exception reading user {username}: {str(e)}")
            return False, latency
            
    async def get_table_user_count(self, session: aiohttp.ClientSession) -> Optional[int]:
        """Get the user count from table metadata"""
        try:
            async with session.get(
                f"{self.api_base_url}/tables/{self.table_id}",
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('userCount', 0)
                else:
                    text = await response.text()
                    self.log_error(f"Failed to get table info. Status: {response.status}, Response: {text}")
                    return None
        except Exception as e:
            self.log_error(f"Exception getting table info: {str(e)}")
            return None
            
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
        """Run the complete load test"""
        self.console.print(f"🚀 Starting Single Table Load Test", style="bold blue")
        self.console.print(f"📊 Target: {self.user_count} concurrent users")
        self.console.print(f"🔗 API Base URL: {self.api_base_url}")
        self.console.print(f"🧪 Table ID: {self.table_id}")
        
        async with aiohttp.ClientSession() as session:
            # Create table first
            if not await self.create_table(session):
                return False
                
            # Phase 1: Concurrent user creation
            self.console.print(f"\n📝 Phase 1: Creating {self.user_count} users concurrently...")
            
            create_latencies = []
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
                transient=True
            ) as progress:
                task = progress.add_task("Creating users...", total=None)
                
                # Create users concurrently
                create_tasks = [
                    self.create_user(session, i) 
                    for i in range(self.user_count)
                ]
                
                create_results = await asyncio.gather(*create_tasks, return_exceptions=True)
                
            # Process create results
            successful_creates = 0
            for result in create_results:
                if isinstance(result, tuple):
                    success, latency = result
                    create_latencies.append(latency)
                    if success:
                        successful_creates += 1
                        
            self.console.print(f"✅ Created {successful_creates}/{self.user_count} users")
            
            # Phase 2: Concurrent user reading
            self.console.print(f"\n📖 Phase 2: Reading {successful_creates} users concurrently...")
            
            read_latencies = []
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
                transient=True
            ) as progress:
                task = progress.add_task("Reading users...", total=None)
                
                # Read users concurrently (only the ones that were created successfully)
                read_tasks = [
                    self.read_user(session, i) 
                    for i in range(successful_creates)
                ]
                
                read_results = await asyncio.gather(*read_tasks, return_exceptions=True)
                
            # Process read results  
            successful_reads = 0
            for result in read_results:
                if isinstance(result, tuple):
                    success, latency = result
                    read_latencies.append(latency)
                    if success:
                        successful_reads += 1
                        
            self.console.print(f"✅ Read {successful_reads}/{successful_creates} users")
            
            # Phase 3: Verify user count
            self.console.print(f"\n🔍 Phase 3: Verifying user count...")
            actual_user_count = await self.get_table_user_count(session)
            
            if actual_user_count is not None:
                if actual_user_count == successful_creates:
                    self.console.print(f"✅ User count matches: {actual_user_count}", style="green")
                else:
                    self.console.print(f"⚠️  User count mismatch: expected {successful_creates}, got {actual_user_count}", style="yellow")
            
        # Print results
        self.console.print(f"\n📈 Performance Results:", style="bold")
        self.print_latency_summary("User Creation", create_latencies)
        self.print_latency_summary("User Reading", read_latencies)
        
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
        print("Usage: export API_BASE_URL=https://your-api.com && python tests/load_single_table.py")
        sys.exit(1)
        
    if not api_url.startswith(('http://', 'https://')):
        print(f"❌ Invalid API URL format: {api_url}")
        sys.exit(1)
        
    return api_url


async def main():
    """Main function"""
    api_base_url = get_api_base_url()
    
    # Run load test
    test = SingleTableLoadTest(api_base_url)
    success = await test.run_load_test()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())