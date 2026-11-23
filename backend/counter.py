"""Line-crossing counter for tracked objects.

A track is counted when the segment between its previous and current anchor point
intersects the counting line. Direction is the side of the line it moved to:
    "in"  : from the left side of A->B to the right side
    "out" : from the right side to the left side
Each track id is counted at most once per direction. If the track's (voted) class
changes after it was counted, `reclassify` moves its count to the new class.
"""
from __future__ import annotations

import time
from collections import Counter, deque
from dataclasses import dataclass, field

Point = tuple[float, float]


def _cross(o: Point, a: Point, b: Point) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def segments_intersect(p1: Point, p2: Point, q1: Point, q2: Point) -> bool:
    """True if segment p1-p2 properly crosses segment q1-q2 (touching an endpoint counts)."""
    d1, d2 = _cross(q1, q2, p1), _cross(q1, q2, p2)
    d3, d4 = _cross(p1, p2, q1), _cross(p1, p2, q2)
    return d1 * d2 <= 0 and d3 * d4 <= 0 and not (d1 == 0 and d2 == 0)


@dataclass
class CrossingEvent:
    timestamp: float
    track_id: int
    cls: str
    direction: str  # "in" | "out"

    def as_dict(self) -> dict:
        return {"timestamp": self.timestamp, "track_id": self.track_id, "class": self.cls, "direction": self.direction}


@dataclass
class LineCounter:
    """Counting line in normalized coordinates (0..1 of frame width/height)."""
    a: Point = (0.0, 0.6)
    b: Point = (1.0, 0.6)
    max_events: int = 500
    counts_in: Counter = field(default_factory=Counter)
    counts_out: Counter = field(default_factory=Counter)
    events: deque = field(default_factory=deque)
    _last: dict = field(default_factory=dict)          # track_id -> last anchor point (normalized)
    _counted: dict = field(default_factory=dict)       # (track_id, direction) -> CrossingEvent

    def set_line(self, a: Point, b: Point) -> None:
        if a == b:
            raise ValueError("line endpoints must differ")
        self.a, self.b = a, b
        self.clear_positions()

