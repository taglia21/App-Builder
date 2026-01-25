"""
Metrics Collection

Provides metrics collection and reporting infrastructure.
"""

import time
import logging
import threading
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections import defaultdict
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@dataclass
class MetricValue:
    """A metric value with metadata."""
    value: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    labels: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "labels": self.labels,
        }


class Counter:
    """
    A monotonically increasing counter.
    
    Use for counting events, requests, errors, etc.
    """
    
    def __init__(
        self,
        name: str,
        description: str = "",
        labels: Optional[List[str]] = None,
    ):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self._values: Dict[tuple, float] = defaultdict(float)
        self._lock = threading.Lock()
    
    def _get_key(self, labels: Dict[str, str]) -> tuple:
        """Get key for labels."""
        return tuple(labels.get(l, "") for l in self.label_names)
    
    def inc(self, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Increment counter.
        
        Args:
            value: Amount to increment (must be positive).
            labels: Label values.
        """
        if value < 0:
            raise ValueError("Counter can only be incremented")
        
        labels = labels or {}
        key = self._get_key(labels)
        
        with self._lock:
            self._values[key] += value
    
    def get(self, labels: Optional[Dict[str, str]] = None) -> float:
        """
        Get counter value.
        
        Args:
            labels: Label values.
        
        Returns:
            Current counter value.
        """
        labels = labels or {}
        key = self._get_key(labels)
        
        with self._lock:
            return self._values[key]
    
    def values(self) -> List[MetricValue]:
        """Get all metric values."""
        with self._lock:
            return [
                MetricValue(
                    value=v,
                    labels=dict(zip(self.label_names, k)),
                )
                for k, v in self._values.items()
            ]


class Gauge:
    """
    A value that can go up and down.
    
    Use for things like queue size, temperature, etc.
    """
    
    def __init__(
        self,
        name: str,
        description: str = "",
        labels: Optional[List[str]] = None,
    ):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self._values: Dict[tuple, float] = defaultdict(float)
        self._lock = threading.Lock()
    
    def _get_key(self, labels: Dict[str, str]) -> tuple:
        """Get key for labels."""
        return tuple(labels.get(l, "") for l in self.label_names)
    
    def set(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Set gauge value.
        
        Args:
            value: New value.
            labels: Label values.
        """
        labels = labels or {}
        key = self._get_key(labels)
        
        with self._lock:
            self._values[key] = value
    
    def inc(self, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment gauge."""
        labels = labels or {}
        key = self._get_key(labels)
        
        with self._lock:
            self._values[key] += value
    
    def dec(self, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Decrement gauge."""
        labels = labels or {}
        key = self._get_key(labels)
        
        with self._lock:
            self._values[key] -= value
    
    def get(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Get gauge value."""
        labels = labels or {}
        key = self._get_key(labels)
        
        with self._lock:
            return self._values[key]
    
    def values(self) -> List[MetricValue]:
        """Get all metric values."""
        with self._lock:
            return [
                MetricValue(
                    value=v,
                    labels=dict(zip(self.label_names, k)),
                )
                for k, v in self._values.items()
            ]


class Histogram:
    """
    A distribution of values.
    
    Use for request latencies, response sizes, etc.
    """
    
    DEFAULT_BUCKETS = (
        0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float("inf")
    )
    
    def __init__(
        self,
        name: str,
        description: str = "",
        labels: Optional[List[str]] = None,
        buckets: Optional[tuple] = None,
    ):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self.buckets = buckets or self.DEFAULT_BUCKETS
        
        self._counts: Dict[tuple, Dict[float, int]] = defaultdict(
            lambda: {b: 0 for b in self.buckets}
        )
        self._sums: Dict[tuple, float] = defaultdict(float)
        self._totals: Dict[tuple, int] = defaultdict(int)
        self._lock = threading.Lock()
    
    def _get_key(self, labels: Dict[str, str]) -> tuple:
        """Get key for labels."""
        return tuple(labels.get(l, "") for l in self.label_names)
    
    def observe(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Observe a value.
        
        Args:
            value: Observed value.
            labels: Label values.
        """
        labels = labels or {}
        key = self._get_key(labels)
        
        with self._lock:
            self._sums[key] += value
            self._totals[key] += 1
            
            for bucket in self.buckets:
                if value <= bucket:
                    self._counts[key][bucket] += 1
    
    def get_stats(
        self, labels: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Get histogram statistics.
        
        Args:
            labels: Label values.
        
        Returns:
            Dictionary with count, sum, and buckets.
        """
        labels = labels or {}
        key = self._get_key(labels)
        
        with self._lock:
            total = self._totals[key]
            return {
                "count": total,
                "sum": self._sums[key],
                "mean": self._sums[key] / total if total > 0 else 0,
                "buckets": dict(self._counts[key]),
            }
    
    @contextmanager
    def time(self, labels: Optional[Dict[str, str]] = None):
        """
        Context manager to time a block of code.
        
        Args:
            labels: Label values.
        
        Yields:
            None.
        """
        start = time.time()
        try:
            yield
        finally:
            self.observe(time.time() - start, labels)


class Timer:
    """
    Convenience class for timing operations.
    
    Wraps a Histogram for easier usage.
    """
    
    def __init__(
        self,
        name: str,
        description: str = "",
        labels: Optional[List[str]] = None,
    ):
        self.histogram = Histogram(
            name=name,
            description=description,
            labels=labels,
            buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, float("inf")),
        )
    
    @property
    def name(self) -> str:
        return self.histogram.name
    
    def record(self, duration: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record a duration in seconds."""
        self.histogram.observe(duration, labels)
    
    @contextmanager
    def time(self, labels: Optional[Dict[str, str]] = None):
        """Time a block of code."""
        with self.histogram.time(labels):
            yield
    
    def get_stats(self, labels: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Get timing statistics."""
        return self.histogram.get_stats(labels)


class MetricsCollector:
    """
    Central registry for metrics.
    
    Collects and exports metrics from the application.
    """
    
    def __init__(self):
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._lock = threading.Lock()
    
    def counter(
        self,
        name: str,
        description: str = "",
        labels: Optional[List[str]] = None,
    ) -> Counter:
        """
        Get or create a counter.
        
        Args:
            name: Counter name.
            description: Counter description.
            labels: Label names.
        
        Returns:
            Counter instance.
        """
        with self._lock:
            if name not in self._counters:
                self._counters[name] = Counter(name, description, labels)
            return self._counters[name]
    
    def gauge(
        self,
        name: str,
        description: str = "",
        labels: Optional[List[str]] = None,
    ) -> Gauge:
        """
        Get or create a gauge.
        
        Args:
            name: Gauge name.
            description: Gauge description.
            labels: Label names.
        
        Returns:
            Gauge instance.
        """
        with self._lock:
            if name not in self._gauges:
                self._gauges[name] = Gauge(name, description, labels)
            return self._gauges[name]
    
    def histogram(
        self,
        name: str,
        description: str = "",
        labels: Optional[List[str]] = None,
        buckets: Optional[tuple] = None,
    ) -> Histogram:
        """
        Get or create a histogram.
        
        Args:
            name: Histogram name.
            description: Histogram description.
            labels: Label names.
            buckets: Bucket boundaries.
        
        Returns:
            Histogram instance.
        """
        with self._lock:
            if name not in self._histograms:
                self._histograms[name] = Histogram(name, description, labels, buckets)
            return self._histograms[name]
    
    def timer(
        self,
        name: str,
        description: str = "",
        labels: Optional[List[str]] = None,
    ) -> Timer:
        """
        Get or create a timer.
        
        Args:
            name: Timer name.
            description: Timer description.
            labels: Label names.
        
        Returns:
            Timer instance.
        """
        # Timers use histograms internally
        return Timer(name, description, labels)
    
    def export(self) -> Dict[str, Any]:
        """
        Export all metrics.
        
        Returns:
            Dictionary of all metric values.
        """
        with self._lock:
            return {
                "counters": {
                    name: [v.to_dict() for v in counter.values()]
                    for name, counter in self._counters.items()
                },
                "gauges": {
                    name: [v.to_dict() for v in gauge.values()]
                    for name, gauge in self._gauges.items()
                },
                "histograms": {
                    name: histogram.get_stats()
                    for name, histogram in self._histograms.items()
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
    
    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()


# Global metrics collector
_collector: Optional[MetricsCollector] = None


def get_metrics() -> MetricsCollector:
    """Get the global metrics collector."""
    global _collector
    if _collector is None:
        _collector = MetricsCollector()
    return _collector


# Pre-defined metrics for common use cases
def get_request_counter() -> Counter:
    """Get request counter."""
    return get_metrics().counter(
        "http_requests_total",
        "Total HTTP requests",
        labels=["method", "path", "status"],
    )


def get_request_duration() -> Histogram:
    """Get request duration histogram."""
    return get_metrics().histogram(
        "http_request_duration_seconds",
        "HTTP request duration in seconds",
        labels=["method", "path"],
    )


def get_active_connections() -> Gauge:
    """Get active connections gauge."""
    return get_metrics().gauge(
        "http_active_connections",
        "Active HTTP connections",
    )


def get_generation_counter() -> Counter:
    """Get generation counter."""
    return get_metrics().counter(
        "generations_total",
        "Total generations",
        labels=["status", "tier"],
    )


def get_generation_duration() -> Histogram:
    """Get generation duration histogram."""
    return get_metrics().histogram(
        "generation_duration_seconds",
        "Generation duration in seconds",
        labels=["stage"],
    )
