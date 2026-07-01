"""
Tab manager: auto-swap between Live Monitor and Shift Summary tabs.
"""
import time
from enum import Enum


class TabName(Enum):
    LIVE = "LIVE"
    SUMMARY = "SUMMARY"


class TabManager:
    """Manage tab switching with auto-swap on a timer."""

    def __init__(self, swap_seconds: float = 5.0):
        """
        Args:
            swap_seconds: interval (seconds) to auto-swap tabs.
        """
        self.swap_seconds = swap_seconds
        self.current_tab = TabName.LIVE
        self.last_swap = time.time()

    def update(self) -> TabName:
        """
        Check if it's time to swap tabs. Returns current tab.
        Call this every frame.
        """
        elapsed = time.time() - self.last_swap
        if elapsed >= self.swap_seconds:
            self.swap()

        return self.current_tab

    def swap(self) -> None:
        """Swap to the other tab."""
        if self.current_tab == TabName.LIVE:
            self.current_tab = TabName.SUMMARY
        else:
            self.current_tab = TabName.LIVE

        self.last_swap = time.time()
        print(f"[TabManager] Swapped to {self.current_tab.value}")

    def force_live(self) -> None:
        """Force switch to LIVE tab."""
        self.current_tab = TabName.LIVE
        self.last_swap = time.time()

    def force_summary(self) -> None:
        """Force switch to SUMMARY tab."""
        self.current_tab = TabName.SUMMARY
        self.last_swap = time.time()

    def get_tab_indicator(self) -> str:
        """Return tab indicator string (e.g., '[1/2]' or '[2/2]')."""
        if self.current_tab == TabName.LIVE:
            return "[1/2]"
        else:
            return "[2/2]"
