"""
Calibration mode: capture and save master image for detection.
"""
import cv2
import pickle
from pathlib import Path
from detector import FrameDetector


class Calibration:
    """Handle master image capture and persistence."""

    MASTER_FILE = "master.pkl"

    def __init__(self, detector: FrameDetector, data_dir: str = "."):
        """
        Args:
            detector: FrameDetector instance to set master on.
            data_dir: directory to store master.pkl (default: current directory).
        """
        self.detector = detector
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.master_path = self.data_dir / self.MASTER_FILE

    def load_master(self) -> bool:
        """Load existing master.pkl if it exists. Returns True if loaded."""
        if self.master_path.exists():
            try:
                with open(self.master_path, "rb") as f:
                    data = pickle.load(f)
                self.detector.master_hash = data["hash"]
                self.detector.master_image = data["image"]
                print(f"[Calibration] Loaded master from {self.master_path}")
                return True
            except Exception as e:
                print(f"[Calibration] Error loading master: {e}")
                return False
        return False

    def save_master(self) -> None:
        """Save current master hash and image to master.pkl."""
        if self.detector.master_hash is None:
            print("[Calibration] No master to save (set one first)")
            return

        data = {
            "hash": self.detector.master_hash,
            "image": self.detector.master_image,
        }
        try:
            with open(self.master_path, "wb") as f:
                pickle.dump(data, f)
            print(f"[Calibration] Saved master to {self.master_path}")
        except Exception as e:
            print(f"[Calibration] Error saving master: {e}")

    def capture_master_from_frame(self, frame, roi: dict) -> None:
        """Capture master from a live frame (typically via 'S' key)."""
        self.detector.set_master(frame, roi)
        self.save_master()
        print("[Calibration] Master captured and saved")

    def has_master(self) -> bool:
        """Return True if a master is currently loaded."""
        return self.detector.master_hash is not None
