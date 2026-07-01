"""
Shift tracking: per-shift piece counts, stats, and daily persistence to today.json.
"""
import json
import os
from datetime import datetime, time as time_type
from pathlib import Path
from typing import Optional, Dict, Tuple


class ShiftTracker:
    """Track piece counts and cycle stats per shift with daily persistence."""

    def __init__(self, config: dict, data_dir: str = "."):
        """
        Args:
            config: dict with shifts config (DAY, EVENING, NIGHT with start/end times).
            data_dir: directory to store today.json (default: current directory).
        """
        self.config = config
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.data_file = self.data_dir / "today.json"
        self.history_dir = self.data_dir / "history"
        self.history_dir.mkdir(parents=True, exist_ok=True)

        self.production_day: Optional[str] = None  # YYYY-MM-DD
        self.shifts: Dict[str, dict] = {}
        self._init_shifts()

    def _init_shifts(self) -> None:
        """Initialize shift structure."""
        for shift_name in ["DAY", "EVENING", "NIGHT"]:
            self.shifts[shift_name] = {
                "count": 0,
                "sum_cycle": 0.0,
                "min_cycle": float("inf"),
                "max_cycle": 0.0,
            }

    def load_or_create(self) -> None:
        """Load today.json if it matches the current day, else create fresh."""
        today = self._get_production_day()
        if self.data_file.exists():
            try:
                with open(self.data_file, "r") as f:
                    data = json.load(f)
                if data.get("production_day") == today:
                    # Same day, load data
                    self.production_day = today
                    self.shifts = data.get("shifts", {})
                    print(f"[ShiftTracker] Loaded today.json for {today}")
                    return
            except Exception as e:
                print(f"[ShiftTracker] Error loading today.json: {e}")

        # Fresh day or load error, create new
        self.production_day = today
        self._init_shifts()
        self.save()
        print(f"[ShiftTracker] Fresh data for production day {today}")

    def add_cycle(self, cycle_time: float) -> str:
        """
        Record a completed cycle.
        Returns the shift name the cycle was attributed to.
        """
        shift_name = self.get_current_shift()
        shift = self.shifts[shift_name]

        shift["count"] += 1
        shift["sum_cycle"] += cycle_time
        shift["min_cycle"] = min(shift["min_cycle"], cycle_time)
        shift["max_cycle"] = max(shift["max_cycle"], cycle_time)

        self.save()
        return shift_name

    def save(self) -> None:
        """Persist current state to today.json."""
        data = {
            "production_day": self.production_day,
            "shifts": self.shifts,
        }
        try:
            with open(self.data_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[ShiftTracker] Error saving today.json: {e}")

    def get_current_shift(self) -> str:
        """Return the shift name for the current time."""
        return self._get_shift_at_time(datetime.now())

    def _get_shift_at_time(self, dt: datetime) -> str:
        """Get shift name for a given datetime."""
        current_time = dt.time()

        for shift_name in ["DAY", "EVENING", "NIGHT"]:
            shift_cfg = self.config["shifts"][shift_name]
            start_str = shift_cfg["start"]
            end_str = shift_cfg["end"]

            start_time = datetime.strptime(start_str, "%H:%M").time()
            # Handle special case: "24:00" means end of day (00:00 of next day)
            if end_str == "24:00":
                end_time = time_type(23, 59, 59)
            else:
                end_time = datetime.strptime(end_str, "%H:%M").time()

            if start_time < end_time:
                # Normal range (e.g., DAY 08:00-16:00)
                if start_time <= current_time < end_time:
                    return shift_name
            else:
                # Wraparound (e.g., NIGHT 00:00-08:00 → after midnight)
                if current_time >= start_time or current_time < end_time:
                    return shift_name

        # Fallback (should not reach)
        return "DAY"

    def get_stats(self, shift_name: str) -> Dict:
        """Get current stats for a shift."""
        shift = self.shifts[shift_name]
        count = shift["count"]
        avg = shift["sum_cycle"] / count if count > 0 else 0.0
        return {
            "count": count,
            "avg": avg,
            "min": shift["min_cycle"] if count > 0 else 0.0,
            "max": shift["max_cycle"] if count > 0 else 0.0,
        }

    def get_all_stats(self) -> Dict[str, Dict]:
        """Get stats for all shifts."""
        return {name: self.get_stats(name) for name in ["DAY", "EVENING", "NIGHT"]}

    def get_today_total(self) -> int:
        """Get total piece count for today."""
        return sum(s["count"] for s in self.shifts.values())

    def _get_production_day(self) -> str:
        """Get production day string (YYYY-MM-DD), reset at 08:00."""
        now = datetime.now()
        # If before 08:00, belong to the previous calendar day's production
        if now.hour < 8:
            # still in NIGHT shift from yesterday
            production_date = now.replace(day=now.day - 1) if now.day > 1 else \
                              now.replace(year=now.year - 1, month=12, day=31)
        else:
            production_date = now

        return production_date.strftime("%Y-%m-%d")

    def should_reset(self) -> bool:
        """Check if we should reset to a fresh day (called at 08:00+)."""
        now = datetime.now()
        if self.production_day is None:
            return True
        day_at_8am = (now if now.hour >= 8 else \
                      now.replace(day=now.day - 1)).strftime("%Y-%m-%d")
        return self.production_day != day_at_8am
