"""
Async Task Queue - Lightweight task processing without external dependencies
Provides non-blocking operation execution for scraping and ingestion tasks
"""

import asyncio
from dataclasses import dataclass, field
from typing import Callable, Any, Dict
from datetime import datetime
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


@dataclass
class Task:
    """Represents a task to be executed"""
    id: str
    func: Callable
    args: tuple
    kwargs: dict
    priority: int = 5
    created_at: datetime = field(default_factory=datetime.utcnow)


class SimpleTaskQueue:
    """
    Lightweight async task queue - no external dependencies
    
    Features:
    - Priority-based task scheduling
    - Thread pool for blocking operations
    - Result storage and retrieval
    - Configurable number of workers
    """
    
    def __init__(self, num_workers: int = 4):
        self.queue = asyncio.PriorityQueue()
        self.workers = []
        self.num_workers = num_workers
        self.executor = ThreadPoolExecutor(max_workers=num_workers)
        self.running = False
        self.results: Dict[str, Dict[str, Any]] = {}
        logger.info(f"Initialized SimpleTaskQueue with {num_workers} workers")
        
    async def add_task(
        self, 
        task_id: str, 
        func: Callable, 
        args: tuple = (), 
        kwargs: dict = None, 
        priority: int = 5
    ) -> str:
        """
        Add task to queue
        
        Args:
            task_id: Unique identifier for the task
            func: Function to execute
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            priority: Priority level (lower number = higher priority)
            
        Returns:
            task_id for status tracking
        """
        kwargs = kwargs or {}
        task = Task(task_id, func, args, kwargs, priority)
        await self.queue.put((priority, task))
        
        # Initialize result tracker
        self.results[task_id] = {
            'status': 'queued',
            'queued_at': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Task {task_id} queued with priority {priority}")
        return task_id
    
    async def worker(self, worker_id: int):
        """
        Worker that processes tasks from queue
        
        Args:
            worker_id: Identifier for this worker
        """
        logger.info(f"Worker-{worker_id} started")
        
        while self.running:
            try:
                # Wait for task with timeout to allow graceful shutdown
                priority, task = await asyncio.wait_for(
                    self.queue.get(), 
                    timeout=1.0
                )
                
                logger.info(f"Worker-{worker_id} processing: {task.id}")
                
                # Update status
                self.results[task.id]['status'] = 'processing'
                self.results[task.id]['started_at'] = datetime.utcnow().isoformat()
                self.results[task.id]['worker_id'] = worker_id
                
                try:
                    # Run blocking tasks in thread pool
                    loop = asyncio.get_event_loop()
                    
                    # Check if function is async
                    if asyncio.iscoroutinefunction(task.func):
                        result = await task.func(*task.args, **task.kwargs)
                    else:
                        result = await loop.run_in_executor(
                            self.executor,
                            lambda: task.func(*task.args, **task.kwargs)
                        )
                    
                    self.results[task.id] = {
                        'status': 'completed',
                        'result': result,
                        'completed_at': datetime.utcnow().isoformat(),
                        'worker_id': worker_id
                    }
                    logger.info(f"✓ Task {task.id} completed successfully")
                    
                except Exception as e:
                    logger.error(f"✗ Task {task.id} failed: {e}", exc_info=True)
                    self.results[task.id] = {
                        'status': 'failed',
                        'error': str(e),
                        'failed_at': datetime.utcnow().isoformat(),
                        'worker_id': worker_id
                    }
                
            except asyncio.TimeoutError:
                # No tasks available, continue loop
                continue
            except Exception as e:
                logger.error(f"Worker-{worker_id} error: {e}", exc_info=True)
        
        logger.info(f"Worker-{worker_id} stopped")
    
    async def start(self):
        """Start all workers"""
        if self.running:
            logger.warning("Task queue already running")
            return
            
        self.running = True
        self.workers = [
            asyncio.create_task(self.worker(i)) 
            for i in range(self.num_workers)
        ]
        logger.info(f"✓ Started {self.num_workers} task queue workers")
    
    async def stop(self):
        """Stop all workers gracefully"""
        logger.info("Stopping task queue...")
        self.running = False
        
        # Wait for workers to finish current tasks
        await asyncio.gather(*self.workers, return_exceptions=True)
        
        # Shutdown thread pool
        self.executor.shutdown(wait=True)
        
        logger.info("✓ Task queue stopped")
    
    def get_result(self, task_id: str) -> Dict[str, Any]:
        """
        Get task result
        
        Args:
            task_id: Task identifier
            
        Returns:
            Dictionary with task status and result/error
        """
        return self.results.get(task_id, {'status': 'not_found'})
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue statistics"""
        statuses = {}
        for result in self.results.values():
            status = result.get('status', 'unknown')
            statuses[status] = statuses.get(status, 0) + 1
        
        return {
            'workers': self.num_workers,
            'queue_size': self.queue.qsize(),
            'total_tasks': len(self.results),
            'status_breakdown': statuses,
            'running': self.running
        }


# Global queue instance - initialized on startup
task_queue = SimpleTaskQueue(num_workers=4)
