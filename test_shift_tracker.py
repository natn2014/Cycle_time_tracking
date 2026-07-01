"""
Unit tests for shift_tracker.py
"""
import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from shift_tracker import ShiftTracker


@pytest.fixture
def config():
    """Standard shift config."""
    return {
        "shifts": {
            "DAY": {"start": "08:00", "end": "16:00"},
            "EVENING": {"start": "16:00", "end": "24:00"},
            "NIGHT": {"start": "00:00", "end": "08:00"},
        }
    }


@pytest.fixture
def temp_data_dir():
    """Temporary directory for test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def tracker(config, temp_data_dir):
    """Create a ShiftTracker with temp data dir."""
    return ShiftTracker(config, data_dir=temp_data_dir)


def test_initialization(tracker):
    """Test that tracker initializes with empty shifts."""
    assert tracker.production_day is None
    for shift in ["DAY", "EVENING", "NIGHT"]:
        assert tracker.shifts[shift]["count"] == 0


def test_load_or_create_fresh_day(tracker):
    """Test that load_or_create creates a fresh file on first run."""
    assert not tracker.data_file.exists()
    tracker.load_or_create()
    assert tracker.data_file.exists()
    assert tracker.production_day is not None


def test_load_or_create_same_day(tracker):
    """Test that load_or_create loads existing data for the same day."""
    # First load (creates fresh)
    tracker.load_or_create()
    day1 = tracker.production_day

    # Add a cycle
    tracker.add_cycle(10.0)
    assert tracker.get_today_total() == 1

    # Create a new tracker instance and load
    tracker2 = ShiftTracker(tracker.config, data_dir=tracker.data_dir)
    tracker2.load_or_create()

    # Should have loaded the same data
    assert tracker2.production_day == day1
    assert tracker2.get_today_total() == 1


def test_add_cycle_updates_counts(tracker):
    """Test that add_cycle increments piece count."""
    tracker.load_or_create()
    assert tracker.get_today_total() == 0

    tracker.add_cycle(10.5)
    assert tracker.get_today_total() == 1

    tracker.add_cycle(12.0)
    assert tracker.get_today_total() == 2


def test_add_cycle_computes_stats(tracker):
    """Test that add_cycle updates min/avg/max."""
    tracker.load_or_create()
    tracker.add_cycle(10.0)
    tracker.add_cycle(20.0)
    tracker.add_cycle(15.0)

    stats = tracker.get_stats("DAY")
    assert stats["count"] == 3
    assert stats["min"] == 10.0
    assert stats["max"] == 20.0
    assert 14.9 < stats["avg"] < 15.1  # avg = (10+20+15)/3 ≈ 15


def test_get_current_shift_day(config):
    """Test shift detection during DAY hours."""
    # 12:00 (noon) should be DAY shift
    mock_time = datetime(2026, 7, 1, 12, 0, 0)
    tracker = ShiftTracker(config)
    shift = tracker._get_shift_at_time(mock_time)
    assert shift == "DAY"


def test_get_current_shift_evening(config):
    """Test shift detection during EVENING hours."""
    # 20:00 (8 PM) should be EVENING shift
    mock_time = datetime(2026, 7, 1, 20, 0, 0)
    tracker = ShiftTracker(config)
    shift = tracker._get_shift_at_time(mock_time)
    assert shift == "EVENING"


def test_get_current_shift_night(config):
    """Test shift detection during NIGHT hours."""
    # 04:00 (4 AM) should be NIGHT shift
    mock_time = datetime(2026, 7, 1, 4, 0, 0)
    tracker = ShiftTracker(config)
    shift = tracker._get_shift_at_time(mock_time)
    assert shift == "NIGHT"


def test_shift_boundaries(config):
    """Test that shift boundaries are respected."""
    tracker = ShiftTracker(config)

    # Just before DAY (07:59)
    t1 = datetime(2026, 7, 1, 7, 59, 0)
    assert tracker._get_shift_at_time(t1) == "NIGHT"

    # At DAY start (08:00)
    t2 = datetime(2026, 7, 1, 8, 0, 0)
    assert tracker._get_shift_at_time(t2) == "DAY"

    # Just before EVENING (15:59)
    t3 = datetime(2026, 7, 1, 15, 59, 0)
    assert tracker._get_shift_at_time(t3) == "DAY"

    # At EVENING start (16:00)
    t4 = datetime(2026, 7, 1, 16, 0, 0)
    assert tracker._get_shift_at_time(t4) == "EVENING"

    # Just before NIGHT (23:59)
    t5 = datetime(2026, 7, 1, 23, 59, 0)
    assert tracker._get_shift_at_time(t5) == "EVENING"

    # At NIGHT start (00:00)
    t6 = datetime(2026, 7, 2, 0, 0, 0)
    assert tracker._get_shift_at_time(t6) == "NIGHT"


def test_persistence_roundtrip(tracker):
    """Test that data survives save/load cycle."""
    tracker.load_or_create()
    tracker.add_cycle(11.5)
    tracker.add_cycle(12.5)
    tracker.add_cycle(10.5)

    # Read the file directly
    with open(tracker.data_file, "r") as f:
        data = json.load(f)

    # Should have persisted the counts (in whatever shift is current)
    total_count = sum(s["count"] for s in data["shifts"].values())
    total_sum = sum(s["sum_cycle"] for s in data["shifts"].values())
    assert total_count == 3
    assert 34.4 < total_sum < 34.6  # 11.5 + 12.5 + 10.5 = 34.5


def test_get_all_stats(tracker):
    """Test that get_all_stats returns all shift stats."""
    tracker.load_or_create()
    tracker.add_cycle(10.0)

    all_stats = tracker.get_all_stats()
    assert "DAY" in all_stats
    assert "EVENING" in all_stats
    assert "NIGHT" in all_stats

    # DAY should have one cycle (assuming current time)
    # EVENING and NIGHT should be empty
    for shift_name in all_stats:
        stats = all_stats[shift_name]
        assert "count" in stats
        assert "avg" in stats
        assert "min" in stats
        assert "max" in stats


def test_get_today_total(tracker):
    """Test that get_today_total sums all shifts."""
    tracker.load_or_create()
    tracker.add_cycle(10.0)
    tracker.add_cycle(12.0)

    total = tracker.get_today_total()
    assert total >= 2  # At least the two we added


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
