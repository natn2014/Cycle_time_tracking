"""
Unit tests for state_machine.py
"""
import pytest
import time
from state_machine import StateMachine, State, CycleResult


@pytest.fixture
def sm():
    """Create a state machine with standard params."""
    return StateMachine(confirm_frames=3, absent_frames=3, min_cycle_seconds=0.1)


def test_initial_state(sm):
    """Test that state machine starts in IDLE."""
    assert sm.state == State.IDLE


def test_idle_to_timing_transition(sm):
    """Test transition from IDLE to TIMING when object is confirmed present."""
    # Feed 3 consecutive "present" frames
    for _ in range(3):
        result = sm.update(is_present=True)
        assert result is None  # No cycle yet

    assert sm.state == State.TIMING
    assert sm.t1 is not None


def test_timing_to_waiting_transition(sm):
    """Test transition from TIMING to WAITING when object is confirmed absent."""
    # Get to TIMING state
    for _ in range(3):
        sm.update(is_present=True)
    assert sm.state == State.TIMING
    t1 = sm.t1

    # Feed 3 consecutive "absent" frames
    for _ in range(3):
        result = sm.update(is_present=False)
        assert result is None

    assert sm.state == State.WAITING_FOR_RETURN
    assert sm.t1 == t1  # t1 should not change


def test_waiting_to_result_transition(sm):
    """Test transition from WAITING to RESULT to TIMING (chained)."""
    # Get to TIMING
    for _ in range(3):
        sm.update(is_present=True)
    t1_first = sm.t1

    # Simulate some time passing
    time.sleep(0.2)

    # Go to WAITING
    for _ in range(3):
        sm.update(is_present=False)
    assert sm.state == State.WAITING_FOR_RETURN

    # Simulate some more time
    time.sleep(0.2)

    # Go back to present -> should trigger RESULT and chain to TIMING
    result = None
    for _ in range(3):
        r = sm.update(is_present=True)
        if r:
            result = r

    # Should have a result
    assert result is not None
    assert isinstance(result, CycleResult)
    assert result.cycle_time >= 0.4  # At least 0.2 + 0.2

    # Should be chained back to TIMING
    assert sm.state == State.TIMING
    # T1 should now be the old T2
    assert sm.t1 == result.t2


def test_minimum_cycle_rejection(sm):
    """Test that cycles faster than min_cycle_seconds are rejected."""
    sm.min_cycle_seconds = 1.0

    # Get to TIMING
    for _ in range(3):
        sm.update(is_present=True)

    # Immediately go to absent
    for _ in range(3):
        sm.update(is_present=False)

    # Immediately back to present (fast)
    result = None
    for _ in range(3):
        r = sm.update(is_present=True)
        if r:
            result = r

    # Should be None because cycle is too fast
    assert result is None
    # State should go back to TIMING (chained with fast T2)
    assert sm.state == State.TIMING


def test_debouncing_present(sm):
    """Test that brief absent flashes don't trigger state change."""
    # Get to TIMING
    for _ in range(3):
        sm.update(is_present=True)
    assert sm.state == State.TIMING

    # One absent frame (not enough to confirm)
    sm.update(is_present=False)
    assert sm.state == State.TIMING

    # Back to present
    sm.update(is_present=True)
    assert sm.state == State.TIMING


def test_debouncing_absent(sm):
    """Test that brief present flashes don't trigger state change."""
    # Get to TIMING
    for _ in range(3):
        sm.update(is_present=True)
    # Go to WAITING
    for _ in range(3):
        sm.update(is_present=False)
    assert sm.state == State.WAITING_FOR_RETURN

    # One present frame (not enough to confirm)
    sm.update(is_present=True)
    assert sm.state == State.WAITING_FOR_RETURN

    # Back to absent
    sm.update(is_present=False)
    assert sm.state == State.WAITING_FOR_RETURN


def test_elapsed_time_in_timing(sm):
    """Test that elapsed time is computed correctly."""
    # Get to TIMING
    for _ in range(3):
        sm.update(is_present=True)

    time.sleep(0.1)
    elapsed = sm.get_elapsed_time()
    assert elapsed is not None
    assert 0.08 < elapsed < 0.15  # Should be roughly 0.1


def test_no_elapsed_in_idle(sm):
    """Test that elapsed time is None in IDLE."""
    elapsed = sm.get_elapsed_time()
    assert elapsed is None


def test_reset_clears_state(sm):
    """Test that reset() returns to IDLE and clears everything."""
    # Get to TIMING
    for _ in range(3):
        sm.update(is_present=True)
    assert sm.state == State.TIMING

    sm.reset()
    assert sm.state == State.IDLE
    assert sm.t1 is None
    assert sm.t2 is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
