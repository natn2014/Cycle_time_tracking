"""
Integration test: detector -> state_machine -> shift_tracker pipeline.
"""
import pytest
import numpy as np
import cv2
import time
import tempfile
from detector import FrameDetector
from state_machine import StateMachine, State
from shift_tracker import ShiftTracker


@pytest.fixture
def detector():
    """Detector with default params."""
    return FrameDetector(canny_low=50, canny_high=150, match_threshold=10)


@pytest.fixture
def state_machine():
    """State machine with default params."""
    return StateMachine(confirm_frames=2, absent_frames=2, min_cycle_seconds=0.1)


@pytest.fixture
def config():
    """Shift config."""
    return {
        "shifts": {
            "DAY": {"start": "08:00", "end": "16:00"},
            "EVENING": {"start": "16:00", "end": "24:00"},
            "NIGHT": {"start": "00:00", "end": "08:00"},
        }
    }


@pytest.fixture
def shift_tracker(config):
    """Shift tracker with temp data dir."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield ShiftTracker(config, data_dir=tmpdir)


@pytest.fixture
def roi():
    """Test ROI."""
    return {"x": 50, "y": 50, "w": 100, "h": 100}


def create_test_frame_with_object():
    """Create a test frame with a white object."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.rectangle(frame, (60, 60), (140, 140), (255, 255, 255), -1)
    return frame


def create_blank_frame():
    """Create a blank frame (no object)."""
    return np.zeros((480, 640, 3), dtype=np.uint8)


def test_full_cycle_pipeline(detector, state_machine, shift_tracker, roi):
    """
    Integration test: full cycle from object detection through shift tracking.

    Scenario:
    1. Set master (object present)
    2. IDLE -> TIMING (object detected)
    3. TIMING -> WAITING (object goes absent)
    4. WAITING -> RESULT (object comes back) -> chained to TIMING
    5. Piece is counted in shift tracker
    """
    # Initialize
    shift_tracker.load_or_create()

    # Step 1: Capture master (object frame)
    master_frame = create_test_frame_with_object()
    detector.set_master(master_frame, roi)
    assert detector.master_hash is not None

    # Step 2: IDLE -> TIMING (feed object frame multiple times)
    for _ in range(2):
        is_present = detector.is_present(master_frame, roi)
        result = state_machine.update(is_present)
        assert is_present == True
        assert result is None  # No cycle yet

    assert state_machine.state == State.TIMING
    t1 = state_machine.t1
    assert t1 is not None

    # Step 3: TIMING -> WAITING (feed blank frame multiple times)
    time.sleep(0.15)  # Simulate some time passing
    blank = create_blank_frame()
    for _ in range(2):
        is_present = detector.is_present(blank, roi)
        result = state_machine.update(is_present)
        assert is_present == False
        assert result is None  # No cycle yet

    assert state_machine.state == State.WAITING_FOR_RETURN
    elapsed_at_waiting = state_machine.get_elapsed_time()
    assert elapsed_at_waiting > 0.1  # Some time has passed

    # Step 4: WAITING -> RESULT (feed object frame again)
    time.sleep(0.15)  # More time passes
    result = None
    for _ in range(2):
        is_present = detector.is_present(master_frame, roi)
        r = state_machine.update(is_present)
        if r:
            result = r
        assert is_present == True

    # Should have a result
    assert result is not None
    assert result.cycle_time >= 0.25  # At least ~0.15 + 0.15
    t2 = result.t2
    assert t2 >= t1

    # Should be back in TIMING (chained)
    assert state_machine.state == State.TIMING
    assert state_machine.t1 == t2  # T1 now points to the old T2

    # Step 5: Piece is recorded in shift tracker
    shift_name = shift_tracker.add_cycle(result.cycle_time)
    assert shift_tracker.get_today_total() == 1
    stats = shift_tracker.get_stats(shift_name)
    assert stats["count"] == 1
    assert stats["min"] == result.cycle_time
    assert stats["max"] == result.cycle_time


def test_multiple_cycles(detector, state_machine, shift_tracker, roi):
    """Test that the pipeline can handle multiple consecutive cycles."""
    shift_tracker.load_or_create()

    # Master
    master = create_test_frame_with_object()
    detector.set_master(master, roi)
    blank = create_blank_frame()

    cycle_times = []

    # Run 3 cycles
    for cycle_num in range(3):
        # IDLE -> TIMING
        for _ in range(2):
            state_machine.update(detector.is_present(master, roi))

        time.sleep(0.1)

        # TIMING -> WAITING
        for _ in range(2):
            state_machine.update(detector.is_present(blank, roi))

        time.sleep(0.1)

        # WAITING -> RESULT
        result = None
        for _ in range(2):
            r = state_machine.update(detector.is_present(master, roi))
            if r:
                result = r

        if result:
            cycle_times.append(result.cycle_time)
            shift_tracker.add_cycle(result.cycle_time)

    # Should have recorded 3 cycles
    assert shift_tracker.get_today_total() >= 3
    assert len(cycle_times) == 3
    # All cycles should have reasonable timing
    for ct in cycle_times:
        assert ct > 0.15  # At least ~0.1 + 0.1


def test_rejected_bounce_cycle(detector, state_machine, shift_tracker, roi):
    """Test that very fast cycles (bounces) are rejected."""
    state_machine.min_cycle_seconds = 1.0  # Strict threshold

    shift_tracker.load_or_create()
    master = create_test_frame_with_object()
    detector.set_master(master, roi)

    # Get to TIMING
    for _ in range(2):
        state_machine.update(detector.is_present(master, roi))
    assert state_machine.state == State.TIMING
    t1_first = state_machine.t1

    # Go to WAITING very quickly (no sleep)
    blank = create_blank_frame()
    for _ in range(2):
        state_machine.update(detector.is_present(blank, roi))
    assert state_machine.state == State.WAITING_FOR_RETURN

    # Come back very quickly (no sleep) -> too fast, should be rejected
    result = None
    for _ in range(2):
        r = state_machine.update(detector.is_present(master, roi))
        if r:
            result = r

    # Should NOT have a result (rejected as too fast)
    assert result is None
    # State should still be TIMING (chained with the fast T2)
    assert state_machine.state == State.TIMING
    # No piece should be counted
    assert shift_tracker.get_today_total() == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
