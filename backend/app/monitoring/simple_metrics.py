"""
Simple Metrics Collection - File-based performance monitoring
Tracks API performance without external dependencies
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class Metrics:
    """Represents a single metric event"""
    endpoint: str
    method: str
    status_code: int
    duration_ms: float
    timestamp: str
    user_agent: str = None
    error: str = None


class MetricsCollector:
    """
    Simple file-based metrics collection
    
    Features:
    - JSONL format for easy parsing
    - Real-time statistics calculation
    - Automatic log rotation
    - Performance tracking per endpoint
    """
    
    def __init__(self, log_file: str = "./logs/metrics.jsonl"):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(exist_ok=True, parents=True)
        self.in_memory_metrics: List[Metrics] = []
        self.max_memory_metrics = 1000  # Keep last 1000 in memory
        logger.info(f"MetricsCollector initialized: {self.log_file.absolute()}")
    
    def record(
        self, 
        endpoint: str, 
        method: str, 
        status_code: int, 
        duration_ms: float,
        user_agent: str = None,
        error: str = None
    ):
        """
        Record a metric
        
        Args:
            endpoint: API endpoint path
            method: HTTP method
            status_code: HTTP status code
            duration_ms: Request duration in milliseconds
            user_agent: Optional user agent string
            error: Optional error message
        """
        metric = Metrics(
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            duration_ms=duration_ms,
            timestamp=datetime.utcnow().isoformat(),
            user_agent=user_agent,
            error=error
        )
        
        # Write to file
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(asdict(metric)) + '\n')
        except Exception as e:
            logger.error(f"Failed to write metric: {e}")
        
        # Keep in memory for fast stats
        self.in_memory_metrics.append(metric)
        if len(self.in_memory_metrics) > self.max_memory_metrics:
            self.in_memory_metrics.pop(0)
    
    def get_stats(self, last_n: int = 100, endpoint: str = None) -> Dict:
        """
        Get statistics for recent requests
        
        Args:
            last_n: Number of recent requests to analyze
            endpoint: Optional filter by specific endpoint
            
        Returns:
            Dictionary with statistics
        """
        # Read from file if we need more than in-memory
        if last_n > len(self.in_memory_metrics):
            metrics = self._read_metrics_from_file(last_n)
        else:
            metrics = self.in_memory_metrics[-last_n:]
        
        # Filter by endpoint if specified
        if endpoint:
            metrics = [m for m in metrics if m.endpoint == endpoint]
        
        if not metrics:
            return {
                'total_requests': 0,
                'message': 'No metrics available'
            }
        
        # Calculate statistics
        total = len(metrics)
        durations = [m.duration_ms for m in metrics]
        avg_duration = sum(durations) / total
        max_duration = max(durations)
        min_duration = min(durations)
        
        # Status code breakdown
        status_codes = {}
        for m in metrics:
            status_codes[m.status_code] = status_codes.get(m.status_code, 0) + 1
        
        # Endpoint breakdown
        endpoints = {}
        for m in metrics:
            endpoints[m.endpoint] = endpoints.get(m.endpoint, 0) + 1
        
        # Method breakdown
        methods = {}
        for m in metrics:
            methods[m.method] = methods.get(m.method, 0) + 1
        
        # Error rate
        errors = sum(1 for m in metrics if m.status_code >= 400)
        error_rate = (errors / total * 100) if total > 0 else 0
        
        # Calculate requests per minute
        if len(metrics) >= 2:
            first_time = datetime.fromisoformat(metrics[0].timestamp)
            last_time = datetime.fromisoformat(metrics[-1].timestamp)
            time_span_minutes = (last_time - first_time).total_seconds() / 60
            rpm = total / time_span_minutes if time_span_minutes > 0 else 0
        else:
            rpm = 0
        
        return {
            'total_requests': total,
            'avg_duration_ms': round(avg_duration, 2),
            'max_duration_ms': round(max_duration, 2),
            'min_duration_ms': round(min_duration, 2),
            'requests_per_minute': round(rpm, 2),
            'error_rate_percent': round(error_rate, 2),
            'status_codes': status_codes,
            'top_endpoints': dict(sorted(
                endpoints.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]),
            'methods': methods,
            'timeframe': {
                'start': metrics[0].timestamp,
                'end': metrics[-1].timestamp
            }
        }
    
    def get_endpoint_stats(self, endpoint: str, last_n: int = 100) -> Dict:
        """
        Get statistics for a specific endpoint
        
        Args:
            endpoint: Endpoint to analyze
            last_n: Number of recent requests
            
        Returns:
            Dictionary with endpoint-specific statistics
        """
        return self.get_stats(last_n=last_n, endpoint=endpoint)
    
    def get_slow_requests(self, threshold_ms: float = 1000, last_n: int = 100) -> List[Dict]:
        """
        Get requests slower than threshold
        
        Args:
            threshold_ms: Duration threshold in milliseconds
            last_n: Number of recent requests to check
            
        Returns:
            List of slow requests
        """
        metrics = self.in_memory_metrics[-last_n:] if last_n <= len(self.in_memory_metrics) else self._read_metrics_from_file(last_n)
        
        slow_requests = [
            asdict(m) for m in metrics 
            if m.duration_ms >= threshold_ms
        ]
        
        # Sort by duration (slowest first)
        slow_requests.sort(key=lambda x: x['duration_ms'], reverse=True)
        
        return slow_requests
    
    def get_errors(self, last_n: int = 100) -> List[Dict]:
        """
        Get error responses (4xx and 5xx)
        
        Args:
            last_n: Number of recent requests to check
            
        Returns:
            List of error requests
        """
        metrics = self.in_memory_metrics[-last_n:] if last_n <= len(self.in_memory_metrics) else self._read_metrics_from_file(last_n)
        
        errors = [
            asdict(m) for m in metrics 
            if m.status_code >= 400
        ]
        
        # Sort by timestamp (most recent first)
        errors.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return errors
    
    def _read_metrics_from_file(self, last_n: int) -> List[Metrics]:
        """
        Read metrics from file
        
        Args:
            last_n: Number of recent metrics to read
            
        Returns:
            List of Metrics objects
        """
        if not self.log_file.exists():
            return []
        
        metrics = []
        
        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        metrics.append(Metrics(**data))
                    except Exception as e:
                        logger.warning(f"Failed to parse metric line: {e}")
        except Exception as e:
            logger.error(f"Failed to read metrics file: {e}")
        
        return metrics[-last_n:]
    
    def rotate_logs(self, max_age_days: int = 7):
        """
        Rotate old log files
        
        Args:
            max_age_days: Maximum age of logs to keep
        """
        if not self.log_file.exists():
            return
        
        try:
            # Read all metrics
            with open(self.log_file, 'r') as f:
                lines = f.readlines()
            
            # Filter recent metrics
            cutoff_time = datetime.utcnow() - timedelta(days=max_age_days)
            recent_lines = []
            
            for line in lines:
                try:
                    data = json.loads(line)
                    timestamp = datetime.fromisoformat(data['timestamp'])
                    if timestamp >= cutoff_time:
                        recent_lines.append(line)
                except Exception:
                    continue
            
            # Write back recent metrics
            with open(self.log_file, 'w') as f:
                f.writelines(recent_lines)
            
            removed = len(lines) - len(recent_lines)
            if removed > 0:
                logger.info(f"Rotated metrics log: removed {removed} old entries")
        
        except Exception as e:
            logger.error(f"Failed to rotate metrics log: {e}")
    
    def clear_logs(self):
        """Clear all metrics logs"""
        if self.log_file.exists():
            self.log_file.unlink()
        self.in_memory_metrics.clear()
        logger.info("Cleared all metrics logs")


# Global metrics instance
metrics = MetricsCollector()
