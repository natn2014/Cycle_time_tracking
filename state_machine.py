"""
State machine for cycle timing: IDLE -> TIMING -> WAITING_FOR_RETURN -> RESULT (chain T1<-T2).
"""
import time
from enum import Enum
from dataclasses import dataclass
from typing import Optional


class State(Enum):
    IDLE = "IDLE"
    TIMING = "TIMING"
    WAITING_FOR_RETURN = "WAITING_FOR_RETURN"
    RESULT = "RESULT"


@dataclass
class CycleResult:
    """Result of a completed cycle."""
    cycle_time: float
    t1: float  # timestamp of first arrival
    t2: float  # timestamp of second arrival


class StateMachine:
    """Manages state transitions and cycle timing."""

    def __init__(self, confirm_frames: int, absent_frames: int, min_cycle_seconds: float):
        """
        Args:
            confirm_frames: consecutive frames needed to confirm PRESENT.
            absent_frames: consecutive frames needed to confirm ABSENT.
            min_cycle_seconds: minimum cycle time to accept (reject bounces).
        """
        self.state = State.IDLE
        self.confirm_frames = confirm_frames
        self.absent_frames = absent_frames
        self.min_cycle_seconds = min_cycle_seconds

        self.t1: Optional[float] = None  # timestamp when first confirmed present
        self.t2: Optional[float] = None  # timestamp when second time confirmed present

        self.present_streak = 0  # consecutive present frames
        self.absent_streak = 0   # consecutive absent frames

        self.last_result: Optional[CycleResult] = None
        self.result_flashed_at: Optional[float] = None  # time we generated the last result

    def update(self, is_present: bool) -> Optional[CycleResult]:
        """
        Update state machine with a frame's detection result.
        Returns a CycleResult if a cycle completes, else None.
        """
        if is_present:
            self.present_streak += 1
            self.absent_streak = 0
        else:
            self.absent_streak += 1
            self.present_streak = 0

        result = None

        if self.state == State.IDLE:
            if self.present_streak >= self.confirm_frames:
                self.state = State.TIMING
                self.t1 = time.time()
                self.present_streak = 0
                print(f"[StateMachine] IDLE -> TIMING (T1={self.t1:.3f})")

        elif self.state == State.TIMING:
            if self.absent_streak >= self.absent_frames:
                self.state = State.WAITING_FOR_RETURN
                self.absent_streak = 0
                print(f"[StateMachine] TIMING -> WAITING_FOR_RETURN")

        elif self.state == State.WAITING_FOR_RETURN:
            if self.present_streak >= self.confirm_frames:
                self.t2 = time.time()
                cycle_time = self.t2 - self.t1

                if cycle_time >= self.min_cycle_seconds:
                    # Valid cycle
                    self.state = State.RESULT
                    self.result_flashed_at = time.time()
                    self.last_result = CycleResult(
                        cycle_time=cycle_time,
                        t1=self.t1,
                        t2=self.t2
                    )
                    print(f"[StateMachine] WAITING -> RESULT (cycle_time={cycle_time:.3f}s)")
                    result = self.last_result
                    # Chain: T1 <- T2 for continuous measurement
                    self.t1 = self.t2
                    self.state = State.TIMING
                    self.present_streak = 0
                    print(f"[StateMachine] RESULT -> TIMING (chained, T1={self.t1:.3f})")
                else:
                    # Too fast, reject and go back to TIMING
                    print(f"[StateMachine] Cycle too fast ({cycle_time:.3f}s), rejected")
                    self.state = State.TIMING
                    self.t1 = self.t2
                    self.present_streak = 0

        return result

    def get_elapsed_time(self) -> Optional[float]:
        """Get elapsed time since T1 if in TIMING or WAITING state."""
        if self.t1 is None:
            return None
        if self.state in (State.TIMING, State.WAITING_FOR_RETURN):
            return time.time() - self.t1
        return None

    def is_result_fresh(self, hold_seconds: float) -> bool:
        """Check if the last result should still be displayed (flashing)."""
        if self.result_flashed_at is None:
            return False
        return (time.time() - self.result_flashed_at) < hold_seconds

    def get_state_label(self) -> str:
        """Return human-readable state label."""
        return self.state.value

    def reset(self) -> None:
        """Full reset to IDLE."""
        self.state = State.IDLE
        self.t1 = None
        self.t2 = None
        self.present_streak = 0
        self.absent_streak = 0
        self.last_result = None
        self.result_flashed_at = None
        print("[StateMachine] Reset to IDLE")
