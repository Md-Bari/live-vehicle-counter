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

    def reset(self) -> None:
        self.counts_in.clear(); self.counts_out.clear(); self.events.clear()
        self._last.clear(); self._counted.clear()

    def update(self, track_id: int, cls: str, point: Point, now: float | None = None) -> CrossingEvent | None:
        """Feed the current anchor point of one track; returns an event if it just crossed the line."""
        prev = self._last.get(track_id)
        self._last[track_id] = point
        if prev is None or not segments_intersect(prev, point, self.a, self.b):
            return None
        side_now = _cross(self.a, self.b, point)
        if side_now == 0:
            return None  # on the line: wait until it is clearly past
        direction = "in" if side_now > 0 else "out"
        key = (track_id, direction)
        if key in self._counted:
            return None
        (self.counts_in if direction == "in" else self.counts_out)[cls] += 1
        ev = CrossingEvent(now if now is not None else time.time(), track_id, cls, direction)
        self._counted[key] = ev
        self.events.append(ev)
        while len(self.events) > self.max_events:
            self.events.popleft()
        return ev

    def reclassify(self, track_id: int, cls: str) -> bool:
        """Move an already counted track to class `cls` (its class estimate improved). True if anything changed."""
        changed = False
        for direction in ("in", "out"):
            ev = self._counted.get((track_id, direction))
            if ev is None or ev.cls == cls:
                continue
            counts = self.counts_in if direction == "in" else self.counts_out
            counts[ev.cls] -= 1
            if counts[ev.cls] <= 0:
                del counts[ev.cls]
            counts[cls] += 1
            ev.cls = cls            # same object as in the event log / CSV list
            changed = True
        return changed

    def clear_positions(self) -> None:
        """Forget last positions (e.g. after a video rewinds) without touching counts."""
        self._last.clear()

    def forget(self, active_ids: set[int]) -> None:
        """Drop last positions of tracks that are gone (keeps memory bounded)."""
        for tid in list(self._last):
            if tid not in active_ids:
                del self._last[tid]

    def snapshot(self, names: list[str]) -> dict:
        per_class = {n: {"in": self.counts_in[n], "out": self.counts_out[n],
                         "total": self.counts_in[n] + self.counts_out[n]} for n in names}
        tin, tout = sum(self.counts_in.values()), sum(self.counts_out.values())
        return {"line": {"a": list(self.a), "b": list(self.b)},
                "total": {"in": tin, "out": tout, "total": tin + tout},
                "per_class": per_class}
