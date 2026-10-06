"""
mas.observability: Structured metrics and logging helpers.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict


def setup_logging(level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("mas")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
        )
        logger.addHandler(handler)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    return logger


@dataclass
class MetricsRegistry:
    counters: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    timings_ms: Dict[str, list] = field(default_factory=lambda: defaultdict(list))
    gauges: Dict[str, float] = field(default_factory=dict)

    def incr(self, name: str, amount: int = 1) -> None:
        self.counters[name] += amount

    def observe_ms(self, name: str, duration_ms: float) -> None:
        self.timings_ms[name].append(duration_ms)

    def set_gauge(self, name: str, value: float) -> None:
        self.gauges[name] = value

    def snapshot(self) -> Dict[str, Any]:
        timing_summary = {}
        for key, values in self.timings_ms.items():
            if not values:
                continue
            timing_summary[key] = {
                "count": len(values),
                "avg_ms": sum(values) / len(values),
                "max_ms": max(values),
            }
        return {
            "counters": dict(self.counters),
            "timings": timing_summary,
            "gauges": dict(self.gauges),
        }


METRICS = MetricsRegistry()
LOGGER = setup_logging()


class Timer:
    def __init__(self, metric_name: str) -> None:
        self.metric_name = metric_name
        self._start = 0.0

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args) -> None:
        elapsed = (time.perf_counter() - self._start) * 1000.0
        METRICS.observe_ms(self.metric_name, elapsed)
