import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from counter import LineCounter, segments_intersect  # noqa: E402

NAMES = ["Car", "Bus"]


def test_segments_intersect():
    assert segments_intersect((0, 0), (1, 1), (0, 1), (1, 0))
    assert not segments_intersect((0, 0), (1, 0), (0, 1), (1, 1))
    assert not segments_intersect((0.5, 0.2), (0.5, 0.4), (0, 0.5), (1, 0.5))   # stops short of line


def test_counts_once_per_direction():
    c = LineCounter(a=(0, 0.5), b=(1, 0.5))
    assert c.update(1, "Car", (0.5, 0.4)) is None
    ev = c.update(1, "Car", (0.5, 0.6))
    assert ev and ev.direction in ("in", "out")
    # jitter back and forth around the line should not count the same direction twice
    c.update(1, "Car", (0.5, 0.45)); c.update(1, "Car", (0.5, 0.65))
    snap = c.snapshot(NAMES)
    assert snap["per_class"]["Car"][ev.direction] == 1


def test_directions_and_classes():
    c = LineCounter(a=(0.5, 0), b=(0.5, 1))          # vertical line
    c.update(1, "Car", (0.2, 0.5)); e1 = c.update(1, "Car", (0.8, 0.5))   # left -> right
    c.update(2, "Bus", (0.8, 0.5)); e2 = c.update(2, "Bus", (0.2, 0.5))   # right -> left
    assert e1.direction != e2.direction
    s = c.snapshot(NAMES)
    assert s["total"]["total"] == 2
    assert s["per_class"]["Car"]["total"] == 1 and s["per_class"]["Bus"]["total"] == 1


