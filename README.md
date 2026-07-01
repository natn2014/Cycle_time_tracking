# Cycle Time Tracker - Production Line Monitor

A real-time cycle time measurement system for Raspberry Pi 5 using USB webcam and computer vision.

**Track production throughput by detecting object silhouette patterns. Measure inter-arrival times continuously. Monitor 3-shift performance.**

![Status](https://img.shields.io/badge/status-production%20ready-brightgreen)
![Tests](https://img.shields.io/badge/tests-33%2F33%20passing-brightgreen)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Features

### Core Functionality
- **Continuous Cycle Measurement:** Detect object arrivals and measure inter-arrival times (takt time)
- **Dual Display Tabs:** 
  - **Tab 1 (Live Monitor):** Real-time video feed + ROI box + elapsed time + rolling statistics
  - **Tab 2 (Shift Summary):** 3-shift piece counts with benchmark bars
- **Per-Shift Tracking:** Automatic attribution to DAY (08:00-16:00), EVENING (16:00-24:00), NIGHT (00:00-08:00)
- **Persistent Daily Totals:** Survives restarts, resets at 08:00 daily

### Technical
- **Edge Detection:** Canny edge detection on ROI
- **Perceptual Hashing:** pHash for robust silhouette matching (lighting-invariant)
- **State Machine:** Continuous chaining (no missed cycles)
- **Debouncing:** Configurable confirm/absent frame thresholds
- **Bounce Rejection:** Minimum cycle time floor to ignore false triggers
- **Full Test Coverage:** 33 unit + integration tests, all passing

---

## Quick Start

### Development (Windows/Linux/Mac)

```bash
# Clone or navigate to project
cd cycle_time_tracking

# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest test_*.py -v

# (Requires webcam) Run application
python main.py
```

### Raspberry Pi (Production)

```bash
# Copy project to Pi
scp -r cycle_time_tracking pi@raspberrypi.local:~/

# Install with auto-start
ssh pi@raspberrypi.local
cd ~/cycle_time_tracking
chmod +x install.sh
./install.sh

# Enable auto-start on boot
sudo systemctl enable cycle-tracker

# Start now
sudo systemctl start cycle-tracker

# Verify
sudo systemctl status cycle-tracker
```

**If you get package errors** (e.g., "unable to locate package"):
```bash
# Use the minimal install script instead
chmod +x install_minimal.sh
./install_minimal.sh
```

**Full deployment guide: [DEPLOYMENT.md](DEPLOYMENT.md)**  
**Troubleshooting: [INSTALL_TROUBLESHOOTING.md](INSTALL_TROUBLESHOOTING.md)**

---

## Project Structure

```
cycle_time_tracking/
├── README.md                  ← You are here
├── DEPLOYMENT.md              ← Raspberry Pi setup guide
├── IMPLEMENTATION_SUMMARY.md  ← Technical details
├── ProjectScope.md            ← Requirements & spec
├── layout.md                  ← UI mockups
│
├── config.yaml                ← Configuration (camera, detection, shifts)
├── requirements.txt           ← Python dependencies
│
├── main.py                    ← Entry point, main loop
├── detector.py                ← Canny + pHash silhouette matching
├── state_machine.py           ← Cycle timing state machine (IDLE→TIMING→WAITING→RESULT)
├── shift_tracker.py           ← Per-shift counting + today.json persistence
├── calibration.py             ← Master image capture/load
├── tabs.py                    ← Auto-swap tab manager
├── display.py                 ← OpenCV rendering (both tabs)
│
├── test_detector.py           ← 8 unit tests
├── test_state_machine.py      ← 10 unit tests
├── test_shift_tracker.py      ← 12 unit tests
├── test_integration.py        ← 3 integration tests
│
├── install.sh                 ← Auto-install script for RPi
├── cycle-tracker.service      ← Systemd service file (auto-start)
│
├── today.json                 ← (Runtime) Daily totals
├── master.pkl                 ← (Runtime) Master silhouette
└── history/                   ← (Runtime) Daily archives
```

---

## Configuration

Edit `config.yaml` to tune:

| Setting | Default | Purpose |
|---------|---------|---------|
| `camera_index` | 0 | USB device index |
| `camera_width` / `height` | 640×480 | Capture resolution |
| `canny_low` / `high` | 50 / 150 | Edge detection sensitivity |
| `match_threshold` | 10 | Silhouette match tolerance (0-64) |
| `confirm_frames` | 5 | Debounce: frames to confirm PRESENT |
| `absent_frames` | 10 | Debounce: frames to confirm ABSENT |
| `min_cycle_seconds` | 2.0 | Reject cycles faster than this |
| `tab_swap_seconds` | 5 | Auto-swap interval |
| `stats_window` | 20 | Rolling stats window size |

**See config.yaml for full reference.**

---

## Usage

### First Run (Calibration)

1. Connect USB webcam + HDMI monitor to RPi
2. Start app: `python main.py` or `sudo systemctl start cycle-tracker`
3. Calibration mode appears on screen
4. Position object in ROI box
5. Press **S** to capture master silhouette
6. Detection loop begins

### Keyboard Controls

| Key | Action |
|-----|--------|
| **S** | Capture new master (calibration mode only) |
| **C** | Re-calibrate during detection (mid-run) |
| **Q** | Quit application |

### Tab Navigation

- Tabs auto-swap every `tab_swap_seconds` (default 5s)
- **Tab 1 (Live):** Video + ROI + real-time cycle timer
- **Tab 2 (Summary):** Shift totals + bars + today's total

---

## Data & Persistence

### today.json (Daily)
```json
{
  "production_day": "2026-07-01",
  "shifts": {
    "DAY": { "count": 142, "sum_cycle": 1746.6, "min_cycle": 9.8, "max_cycle": 18.1 },
    "EVENING": { "count": 108, "sum_cycle": 1522.8, "min_cycle": 10.2, "max_cycle": 21.5 },
    "NIGHT": { "count": 89, "sum_cycle": 1424.0, "min_cycle": 11.0, "max_cycle": 25.3 }
  }
}
```

**Reset:** Automatically at 08:00 (DAY shift start). Previous day archived to `history/YYYY-MM-DD.json`.

### master.pkl
Binary file holding master silhouette hash + reference image. Created on first calibration, reusable across restarts.

---

## Test Coverage

**33 tests, all passing:**

| Module | Tests | Status |
|--------|-------|--------|
| detector | 8 | ✅ |
| state_machine | 10 | ✅ |
| shift_tracker | 12 | ✅ |
| integration | 3 | ✅ |

**Run tests:**
```bash
python -m pytest test_*.py -v
```

**Run specific suite:**
```bash
python -m pytest test_detector.py -v
```

---

## Hardware

### Recommended

- **Compute:** Raspberry Pi 5 (8 GB RAM)
- **Camera:** USB webcam (UVC-compatible, 30+ fps at 640×480)
- **Display:** HDMI monitor
- **OS:** Raspberry Pi OS (Bookworm, 64-bit)

### Tested

- ✅ Raspberry Pi 5, 8 GB, Logitech C920 USB webcam
- ✅ Raspberry Pi OS 64-bit Bookworm
- ✅ Python 3.11+

---

## Performance

On Raspberry Pi 5 with 640×480 @ 30 fps:

- **Frame processing:** ~30-50ms (30 fps sustainable)
- **Memory:** ~200-300 MB (Python + OpenCV + video buffer)
- **CPU:** 40-60% single core (frame capture + Canny + pHash)

**Tips:**
- Reduce `target_fps` if CPU-bound
- Cap `camera_width/height` if USB bandwidth limited
- Disable fullscreen mode if rendering is slow

---

## Troubleshooting

### Camera Not Detected
```bash
# List connected cameras
ls /dev/video*

# Get camera info
v4l2-ctl -d /dev/video0 --list-formats-ext

# Update config.yaml: camera_index
```

### Service Won't Start
```bash
# Check for errors
sudo systemctl status cycle-tracker
journalctl -u cycle-tracker -n 20
```

### Detection Not Working
- Check lighting (Canny edge detection needs contrast)
- Adjust `canny_low`/`high` in config.yaml
- Lower `match_threshold` if master doesn't match similar objects
- Increase `confirm_frames` if noisy

### Data Not Persisting
- Check file permissions: `ls -l today.json`
- Verify shift times in config.yaml match current time
- Check system clock: `date`

**See [DEPLOYMENT.md](DEPLOYMENT.md) for full troubleshooting.**

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│ USB Webcam (30 fps, 640×480)                        │
└─────────────────────────────────────────────────────┘
                      ↓
        ┌─ ROI Crop → Grayscale → Canny Edge
        │
   ┌────┴─────────────────────────────────────────┐
   │  pHash (Perceptual Hash)                      │
   │  Hamming Distance vs. Master Hash             │
   └─────────────────────────┬──────────────────────┘
                      ↓ (is_present: bool)
   ┌─────────────────────────────────────────────┐
   │ State Machine                               │
   │ IDLE → TIMING → WAITING → RESULT (chain)    │
   │ (debounce + bounce rejection)               │
   └─────────────────────────┬──────────────────────┘
                      ↓ (on RESULT: CycleResult)
   ┌─────────────────────────────────────────────┐
   │ Shift Tracker                               │
   │ +1 piece → current_shift bucket             │
   │ Persist to today.json                       │
   └─────────────────────────┬──────────────────────┘
                      ↓
   ┌─────────────────────────────────────────────┐
   │ Display (OpenCV)                            │
   │ ├─ Tab 1: Live feed + ROI + elapsed time   │
   │ └─ Tab 2: Shift summary + bars (5s swap)   │
   └─────────────────────────┬──────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│ HDMI Monitor Output                                │
└─────────────────────────────────────────────────────┘
```

---

## Data Flow Example

**Scenario:** Object arrives at camera.

1. **T=0.00s:** Object enters ROI
   - `is_present = True` (frame 1-5, debounce)
   - State: IDLE → TIMING
   - Timer starts: T₁ = 0.00

2. **T=0.50s:** Object leaves ROI
   - `is_present = False` (frame 1-10, debounce)
   - State: TIMING → WAITING_FOR_RETURN
   - Timer continues

3. **T=1.20s:** Object returns to ROI
   - `is_present = True` (frame 1-5, debounce)
   - Cycle time = 1.20 - 0.00 = 1.20s
   - State: WAITING → RESULT
   - **+1 piece to current shift**
   - T₁ ← T₂ (continuous chaining)
   - State: RESULT → TIMING (back to timing immediately)

4. **Persistence:**
   - today.json updated: shift.count += 1
   - Display updated: Tab 2 shows new total

---

## Development Notes

### Adding Features

1. **New detection method?** → Modify `detector.py`
2. **New state logic?** → Update `state_machine.py`
3. **New shift rule?** → Tune `shift_tracker.py`
4. **UI changes?** → Edit `display.py`

**Always add tests** in `test_*.py` — run before committing.

### Performance Profiling

```bash
# Profile main loop
python -m cProfile -s cumtime main.py
```

### Debugging

```bash
# Run with console output
python main.py

# Manually activate venv and test modules
source venv/bin/activate
python -c "from detector import FrameDetector; print('✓ detector imports')"
```

---

## License

MIT License. See LICENSE file (if included).

---

## Support & Contact

For issues or questions:
1. Check [DEPLOYMENT.md](DEPLOYMENT.md) for setup help
2. Review [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) for technical details
3. Run tests: `pytest test_*.py -v`
4. Check logs: `journalctl -u cycle-tracker -f`

---

## Changelog

### v1.0.0 (Current)
- ✅ Core cycle timing (continuous, T₁←T₂ chaining)
- ✅ Per-shift tracking (DAY/EVENING/NIGHT)
- ✅ Dual-tab display (Live + Summary)
- ✅ Auto-calibration + master persistence
- ✅ Systemd auto-start
- ✅ Full test coverage (33 tests)
- ✅ Raspberry Pi deployment ready

### Future (v1.1+)
- [ ] CSV logging per cycle
- [ ] Remote HTTP API dashboard
- [ ] Multi-camera support
- [ ] Historical trend analysis
- [ ] Alert thresholds (cycle time anomalies)
- [ ] Database backend (PostgreSQL)

---

**Ready for production. Deploy to Raspberry Pi and start measuring.**
