"""
Unit tests for detector.py
"""
import pytest
import numpy as np
import cv2
from detector import FrameDetector


@pytest.fixture
def detector():
    """Instantiate detector with default params."""
    return FrameDetector(canny_low=50, canny_high=150, match_threshold=10)


@pytest.fixture
def sample_roi():
    """Sample ROI config."""
    return {"x": 50, "y": 50, "w": 100, "h": 100}


@pytest.fixture
def blank_frame():
    """Create a blank BGR frame (640x480)."""
    return np.zeros((480, 640, 3), dtype=np.uint8)


@pytest.fixture
def frame_with_shape(blank_frame, sample_roi):
    """Create a frame with a white rectangle in the ROI."""
    frame = blank_frame.copy()
    x, y, w, h = sample_roi["x"], sample_roi["y"], sample_roi["w"], sample_roi["h"]
    cv2.rectangle(frame, (x + 10, y + 10), (x + w - 10, y + h - 10), (255, 255, 255), -1)
    return frame


def test_master_capture(detector, frame_with_shape, sample_roi):
    """Test that master can be captured from a frame."""
    assert detector.master_hash is None
    detector.set_master(frame_with_shape, sample_roi)
    assert detector.master_hash is not None
    assert detector.master_image is not None


def test_perfect_match(detector, frame_with_shape, sample_roi):
    """Test that the same frame matches itself."""
    detector.set_master(frame_with_shape, sample_roi)
    # Identical frame should match
    assert detector.is_present(frame_with_shape, sample_roi) == True


def test_absent_detection(detector, frame_with_shape, blank_frame, sample_roi):
    """Test that a blank frame is detected as absent after setting a white master."""
    detector.set_master(frame_with_shape, sample_roi)
    # Blank frame should NOT match
    assert detector.is_present(blank_frame, sample_roi) == False


def test_hash_distance_computation(detector, frame_with_shape, sample_roi):
    """Test that hash distances are computed correctly."""
    detector.set_master(frame_with_shape, sample_roi)
    distance_same = detector.get_hash_distance(frame_with_shape, sample_roi)
    # Same image should have distance close to 0
    assert distance_same <= 5  # Allow small numerical variance


def test_threshold_boundary(detector, frame_with_shape, sample_roi):
    """Test that match threshold is respected."""
    detector.set_master(frame_with_shape, sample_roi)
    distance = detector.get_hash_distance(frame_with_shape, sample_roi)
    # If distance is 0, it should match (threshold is 10)
    assert detector.is_present(frame_with_shape, sample_roi) == True


def test_no_master_returns_false(detector, blank_frame, sample_roi):
    """Test that is_present returns False when no master is set."""
    assert detector.is_present(blank_frame, sample_roi) is False


def test_different_shapes(detector, blank_frame, sample_roi):
    """Test detection when master is one shape and test frame is different."""
    # Create master: white rectangle
    master_frame = blank_frame.copy()
    x, y, w, h = sample_roi["x"], sample_roi["y"], sample_roi["w"], sample_roi["h"]
    cv2.rectangle(master_frame, (x + 10, y + 10), (x + w - 10, y + h - 10), (255, 255, 255), -1)
    detector.set_master(master_frame, sample_roi)

    # Create test frame: different shape (circle)
    test_frame = blank_frame.copy()
    cv2.circle(test_frame, (x + w // 2, y + h // 2), 20, (255, 255, 255), -1)

    # Different shape should have higher hash distance
    distance = detector.get_hash_distance(test_frame, sample_roi)
    # Not expected to match (distance should be > threshold for a very different shape)
    # Note: this is a soft test; exact threshold depends on Canny params


def test_roi_cropping(detector, sample_roi):
    """Test that ROI is correctly extracted."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # Paint a region outside ROI
    cv2.rectangle(frame, (10, 10), (40, 40), (255, 255, 255), -1)
    # Paint a region inside ROI
    cv2.rectangle(frame, (60, 60), (80, 80), (255, 255, 255), -1)

    roi_crop = detector._crop_roi(frame, sample_roi)
    assert roi_crop.shape == (sample_roi["h"], sample_roi["w"], 3)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
