"""
Frame detector: edge detection + perceptual hashing for silhouette matching.
"""
import cv2
import numpy as np
import imagehash
from PIL import Image


class FrameDetector:
    """Detect object presence by comparing frame edges to master hash."""

    def __init__(self, canny_low: int, canny_high: int, match_threshold: int):
        """
        Args:
            canny_low: Canny edge detection lower threshold.
            canny_high: Canny edge detection upper threshold.
            match_threshold: Hamming distance threshold for a match (0-64).
        """
        self.canny_low = canny_low
        self.canny_high = canny_high
        self.match_threshold = match_threshold
        self.master_hash = None
        self.master_image = None

    def set_master(self, frame: np.ndarray, roi: dict) -> None:
        """Capture and set the master image hash from a frame ROI."""
        roi_frame = self._crop_roi(frame, roi)
        edges = self._get_edges(roi_frame)
        self.master_hash = self._compute_hash(edges)
        self.master_image = roi_frame
        print(f"[Detector] Master hash set: {self.master_hash}")

    def is_present(self, frame: np.ndarray, roi: dict) -> bool:
        """
        Check if the object (matching master silhouette) is present in the ROI.
        Returns True if Hamming distance to master hash <= threshold.
        """
        if self.master_hash is None:
            return False

        roi_frame = self._crop_roi(frame, roi)
        edges = self._get_edges(roi_frame)
        current_hash = self._compute_hash(edges)
        distance = self._hamming_distance(self.master_hash, current_hash)
        return distance <= self.match_threshold

    def get_hash_distance(self, frame: np.ndarray, roi: dict) -> int:
        """Return the Hamming distance to the master hash (for debugging)."""
        if self.master_hash is None:
            return 64  # No master; treat as fully absent.

        roi_frame = self._crop_roi(frame, roi)
        edges = self._get_edges(roi_frame)
        current_hash = self._compute_hash(edges)
        return self._hamming_distance(self.master_hash, current_hash)

    @staticmethod
    def _crop_roi(frame: np.ndarray, roi: dict) -> np.ndarray:
        """Extract ROI rectangle from frame."""
        x, y, w, h = roi["x"], roi["y"], roi["w"], roi["h"]
        return frame[y : y + h, x : x + w]

    def _get_edges(self, roi_frame: np.ndarray) -> np.ndarray:
        """Convert ROI to grayscale and apply Canny edge detection."""
        gray = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, self.canny_low, self.canny_high)
        return edges

    @staticmethod
    def _compute_hash(edges: np.ndarray) -> imagehash.ImageHash:
        """Compute pHash from edge image."""
        pil_image = Image.fromarray(edges)
        return imagehash.phash(pil_image)

    @staticmethod
    def _hamming_distance(hash1: imagehash.ImageHash, hash2: imagehash.ImageHash) -> int:
        """Compute Hamming distance between two hashes."""
        return (hash1 - hash2)
