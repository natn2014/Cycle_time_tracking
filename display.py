"""
Display rendering: Tab 1 (Live Monitor) and Tab 2 (Shift Summary).
"""
import cv2
import numpy as np
from typing import List, Optional, Tuple
from state_machine import StateMachine, State
from shift_tracker import ShiftTracker
from tabs import TabName


class Display:
    """Render live feed and UI overlays to screen."""

    def __init__(self, width: int = 1280, height: int = 720, fullscreen: bool = True):
        """
        Args:
            width, height: display resolution.
            fullscreen: whether to render fullscreen.
        """
        self.width = width
        self.height = height
        self.fullscreen = fullscreen
        self.window_name = "Cycle Time Tracker"

        if fullscreen:
            cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
            cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        else:
            cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(self.window_name, width, height)

    def render_live_tab(
        self,
        frame: np.ndarray,
        roi: dict,
        state_machine: StateMachine,
        shift_tracker: ShiftTracker,
        tab_indicator: str,
    ) -> None:
        """
        Render Tab 1: Live monitor with live feed, ROI, state, elapsed time, and stats.
        """
        canvas = self._create_canvas()

        # Left zone: live feed + ROI
        feed_zone = self._render_feed_zone(canvas, frame, roi, state_machine)

        # Right zone: info panel
        self._render_info_panel(canvas, state_machine, shift_tracker, tab_indicator)

        cv2.imshow(self.window_name, canvas)

    def render_summary_tab(self, shift_tracker: ShiftTracker, tab_indicator: str) -> None:
        """
        Render Tab 2: Shift summary with piece counts and bars.
        """
        canvas = self._create_canvas()

        # Header
        cv2.putText(
            canvas,
            "SHIFT SUMMARY",
            (50, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (255, 255, 255),
            2,
        )
        cv2.putText(
            canvas,
            tab_indicator,
            (self.width - 150, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (200, 200, 200),
            1,
        )

        # Get all stats
        all_stats = shift_tracker.get_all_stats()
        shift_names = ["DAY", "EVENING", "NIGHT"]

        # Find max count for bar scaling
        max_count = max((all_stats[s]["count"] for s in shift_names), default=1)
        max_count = max(max_count, 1)  # Avoid division by zero

        # Current shift
        current_shift = shift_tracker.get_current_shift()

        # Render each shift row
        y_offset = 120
        row_height = 100

        for i, shift_name in enumerate(shift_names):
            stats = all_stats[shift_name]
            is_current = shift_name == current_shift

            self._render_shift_row(
                canvas,
                y_offset + i * row_height,
                shift_name,
                stats,
                max_count,
                is_current,
            )

        # Today total
        total = shift_tracker.get_today_total()
        cv2.putText(
            canvas,
            f"TODAY TOTAL: {total} pcs",
            (50, self.height - 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (255, 255, 255),
            2,
        )

        cv2.imshow(self.window_name, canvas)

    def _create_canvas(self) -> np.ndarray:
        """Create a blank canvas."""
        return np.zeros((self.height, self.width, 3), dtype=np.uint8)

    def _render_feed_zone(self, canvas: np.ndarray, frame: np.ndarray, roi: dict, sm: StateMachine) -> None:
        """Render left zone: live feed with ROI box."""
        # Resize frame to fit left half
        feed_width = self.width // 2
        feed_height = self.height

        # Resize frame
        resized_frame = cv2.resize(frame, (feed_width, feed_height))

        # Overlay ROI box scaled to fit resized frame
        roi_x = int(roi["x"] * feed_width / frame.shape[1])
        roi_y = int(roi["y"] * feed_height / frame.shape[0])
        roi_w = int(roi["w"] * feed_width / frame.shape[1])
        roi_h = int(roi["h"] * feed_height / frame.shape[0])

        # ROI color based on state
        if sm.state == State.TIMING:
            roi_color = (0, 255, 255)  # Yellow (present)
            thickness = 2
        else:
            roi_color = (255, 255, 255)  # White dashed (absent)
            thickness = 1

        cv2.rectangle(resized_frame, (roi_x, roi_y), (roi_x + roi_w, roi_y + roi_h), roi_color, thickness)

        # Place resized frame on canvas
        canvas[:, :feed_width] = resized_frame

    def _render_info_panel(
        self,
        canvas: np.ndarray,
        state_machine: StateMachine,
        shift_tracker: ShiftTracker,
        tab_indicator: str,
    ) -> None:
        """Render right zone: state badge, elapsed time, stats."""
        panel_x = self.width // 2 + 20

        # Header / tab indicator
        cv2.putText(
            canvas,
            tab_indicator,
            (self.width - 100, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (200, 200, 200),
            1,
        )

        # State badge
        state_label = state_machine.get_state_label()
        state_color = self._get_state_color(state_machine.state)
        cv2.putText(
            canvas,
            f"● {state_label}",
            (panel_x, 100),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            state_color,
            2,
        )

        # Elapsed time or last cycle result
        elapsed = state_machine.get_elapsed_time()
        if state_machine.is_result_fresh(result_hold_seconds=2.0):
            # Show result flashing
            time_str = f"{state_machine.last_result.cycle_time:.2f} s"
            time_color = (0, 255, 0)  # Green
        elif elapsed is not None:
            time_str = f"{elapsed:.2f} s"
            time_color = (255, 255, 255)  # White
        else:
            time_str = "--.- s"
            time_color = (100, 100, 100)  # Gray

        cv2.putText(
            canvas,
            time_str,
            (panel_x, 180),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.5,
            time_color,
            3,
        )

        # Stats (last cycle, min, avg, max)
        if state_machine.last_result:
            last_cycle = state_machine.last_result.cycle_time
        else:
            last_cycle = None

        cv2.putText(
            canvas,
            "─" * 30,
            (panel_x, 230),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (150, 150, 150),
            1,
        )

        current_shift = shift_tracker.get_current_shift()
        stats = shift_tracker.get_stats(current_shift)

        if last_cycle:
            cv2.putText(
                canvas,
                f"Last cycle  {last_cycle:.2f} s",
                (panel_x, 270),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (200, 200, 200),
                1,
            )

        stats_line = f"Min  {stats['min']:.2f}  |  Avg  {stats['avg']:.2f}  |  Max  {stats['max']:.2f}"
        cv2.putText(
            canvas,
            stats_line,
            (panel_x, 320),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (180, 180, 180),
            1,
        )

    def _render_shift_row(
        self,
        canvas: np.ndarray,
        y: int,
        shift_name: str,
        stats: dict,
        max_count: int,
        is_current: bool,
    ) -> None:
        """Render a single shift row with bar chart."""
        x = 50
        bar_width = self.width - 200

        # Shift name and indicator
        if is_current:
            prefix = "▶ "
            text_color = (0, 255, 255)  # Cyan
        else:
            prefix = "  "
            text_color = (150, 150, 150)  # Gray

        cv2.putText(
            canvas,
            f"{prefix}{shift_name:<8} {stats['count']:3d} pcs",
            (x, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            text_color,
            1,
        )

        # Bar chart
        bar_filled = int((stats["count"] / max_count) * bar_width) if max_count > 0 else 0
        bar_color = (0, 255, 255) if is_current else (150, 150, 150)  # Cyan or gray

        cv2.rectangle(
            canvas,
            (x + 150, y - 15),
            (x + 150 + bar_filled, y + 5),
            bar_color,
            -1,
        )
        cv2.rectangle(
            canvas,
            (x + 150, y - 15),
            (x + 150 + bar_width, y + 5),
            (100, 100, 100),
            1,
        )

        # Stats
        avg_str = f"Avg {stats['avg']:.1f}s | Min {stats['min']:.1f}s | Max {stats['max']:.1f}s"
        cv2.putText(
            canvas,
            avg_str,
            (x, y + 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (180, 180, 180),
            1,
        )

    @staticmethod
    def _get_state_color(state: State) -> Tuple[int, int, int]:
        """Return BGR color for state badge."""
        if state == State.IDLE:
            return (128, 128, 128)  # Gray
        elif state == State.TIMING:
            return (255, 0, 0)  # Blue
        elif state == State.WAITING_FOR_RETURN:
            return (0, 165, 255)  # Orange
        elif state == State.RESULT:
            return (0, 255, 0)  # Green
        else:
            return (255, 255, 255)  # White

    def close(self) -> None:
        """Close the display window."""
        cv2.destroyAllWindows()
