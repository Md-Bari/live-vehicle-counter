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


