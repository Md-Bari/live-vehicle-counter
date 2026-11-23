import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from counter import LineCounter, segments_intersect  # noqa: E402

NAMES = ["Car", "Bus"]


def test_segments_intersect():
    assert segments_intersect((0, 0), (1, 1), (0, 1), (1, 0))
    assert not segments_intersect((0, 0), (1, 0), (0, 1), (1, 1))
    assert not segments_intersect((0.5, 0.2), (0.5, 0.4), (0, 0.5), (1, 0.5))   # stops short of line


