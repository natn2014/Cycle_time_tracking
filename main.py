"""
Main entry point: wire detector, state machine, shift tracker, calibration, tabs, and display.
"""
import cv2
import yaml
from pathlib import Path
from detector import FrameDetector
from state_machine import StateMachine
from shift_tracker import ShiftTracker
from calibration import Calibration
from tabs import TabManager, TabName
from display import Display


class CycleTimeTracker:
    """Main application: orchestrate all modules."""

    def __init__(self, config_path: str = "config.yaml", data_dir: str = "."):
        """
        Args:
            config_path: path to config.yaml.
            data_dir: directory for data files (master.pkl, today.json, etc.).
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Load config
        self.config = self._load_config(config_path)

        # Initialize modules
        self.detector = FrameDetector(
            canny_low=self.config["canny_low"],
            canny_high=self.config["canny_high"],
            match_threshold=self.config["match_threshold"],
        )
        self.state_machine = StateMachine(
            confirm_frames=self.config["confirm_frames"],
            absent_frames=self.config["absent_frames"],
            min_cycle_seconds=self.config["min_cycle_seconds"],
        )
        self.shift_tracker = ShiftTracker(self.config, data_dir=str(self.data_dir))
        self.calibration = Calibration(self.detector, data_dir=str(self.data_dir))
        self.tab_manager = TabManager(swap_seconds=self.config["tab_swap_seconds"])
        self.display = Display(
            fullscreen=self.config["display_fullscreen"],
        )

        # Camera
        self.cap = cv2.VideoCapture(self.config["camera_index"])
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config["camera_width"])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config["camera_height"])
        self.cap.set(cv2.CAP_PROP_FPS, self.config["target_fps"])

        # Stats for rolling window (Tab 1)
        self.cycle_history = []
        self.max_history = self.config.get("stats_window", 20)

    def _load_config(self, config_path: str) -> dict:
        """Load YAML config."""
        try:
            with open(config_path, "r") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"[Main] Config file not found: {config_path}")
            raise

    def run(self):
        """Main loop."""
        print("[Main] Starting Cycle Time Tracker...")

        # Load shift tracker data
        self.shift_tracker.load_or_create()

        # Try to load existing master, else enter calibration
        if not self.calibration.load_master():
            print("[Main] No master found. Entering calibration mode.")
            print("[Main] Press 'S' to capture master, 'C' to re-calibrate, 'Q' to quit.")
            self._calibration_loop()

        if not self.calibration.has_master():
            print("[Main] Calibration cancelled. Exiting.")
            return

        # Main detection loop
        print("[Main] Starting detection loop...")
        print("[Main] Press 'Q' to quit.")
        self._detection_loop()

        self.cleanup()

    def _calibration_loop(self):
        """Loop until master is captured or user quits."""
        roi = self.config["roi"]

        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("[Main] Failed to read frame")
                break

            # Simple display with ROI overlay
            display_frame = frame.copy()
            x, y, w, h = roi["x"], roi["y"], roi["w"], roi["h"]
            cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 255, 255), 2)
            cv2.putText(
                display_frame,
                "CALIBRATION MODE - Press S to save master",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2,
            )

            cv2.imshow("Cycle Time Tracker", display_frame)

            key = cv2.waitKey(30) & 0xFF
            if key == ord("s") or key == ord("S"):
                self.calibration.capture_master_from_frame(frame, roi)
                print("[Main] Master captured. Press any key to start detection.")
                cv2.waitKey(1000)
                break
            elif key == ord("q") or key == ord("Q"):
                print("[Main] Calibration cancelled by user.")
                break

    def _detection_loop(self):
        """Main detection and display loop."""
        roi = self.config["roi"]

        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("[Main] Failed to read frame")
                break

            # Detect
            is_present = self.detector.is_present(frame, roi)

            # Update state machine
            cycle_result = self.state_machine.update(is_present)
            if cycle_result:
                # Cycle completed
                shift_name = self.shift_tracker.add_cycle(cycle_result.cycle_time)
                self.cycle_history.append(cycle_result.cycle_time)
                if len(self.cycle_history) > self.max_history:
                    self.cycle_history.pop(0)
                print(f"[Main] Cycle {len(self.cycle_history)}: {cycle_result.cycle_time:.2f}s ({shift_name})")

            # Update tab
            current_tab = self.tab_manager.update()
            tab_indicator = self.tab_manager.get_tab_indicator()

            # Render
            if current_tab == TabName.LIVE:
                self.display.render_live_tab(
                    frame,
                    roi,
                    self.state_machine,
                    self.shift_tracker,
                    tab_indicator,
                )
            else:
                self.display.render_summary_tab(self.shift_tracker, tab_indicator)

            # Handle keyboard
            key = cv2.waitKey(30) & 0xFF
            if key == ord("q") or key == ord("Q"):
                print("[Main] Quit requested by user.")
                break
            elif key == ord("c") or key == ord("C"):
                print("[Main] Re-calibration requested. Entering calibration mode.")
                self._calibration_loop()
                if not self.calibration.has_master():
                    print("[Main] Calibration cancelled. Exiting.")
                    break
                print("[Main] Resuming detection.")

    def cleanup(self):
        """Clean up resources."""
        self.cap.release()
        self.display.close()
        cv2.destroyAllWindows()
        print("[Main] Cleanup complete.")


if __name__ == "__main__":
    app = CycleTimeTracker(config_path="config.yaml", data_dir=".")
    app.run()
