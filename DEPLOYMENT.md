# Deployment Guide: Raspberry Pi 5

Quick start for deploying Cycle Time Tracker to Raspberry Pi 5 with automatic startup.

## Prerequisites

- Raspberry Pi 5 (8 GB RAM recommended)
- Raspberry Pi OS (Bookworm, 64-bit)
- USB webcam (UVC-compatible)
- HDMI monitor
- Internet connection (for installation)
- SSH access or terminal on Pi

## Installation (Automated)

### 1. Clone or Copy Files to Raspberry Pi

```bash
# On your development machine, copy files to Pi
scp -r cycle_time_tracking pi@raspberrypi.local:/home/pi/

# Or via USB stick / direct copy
```

### 2. Run Installation Script

```bash
# SSH into Pi
ssh pi@raspberrypi.local

# Navigate to project
cd ~/cycle_time_tracking

# Make script executable
chmod +x install.sh

# Run installation (installs dependencies + creates systemd service)
./install.sh

# Or specify custom directory and user
./install.sh /opt/cycle-tracker pi
```

The script will:
- ✅ Update system packages
- ✅ Install Python, OpenCV, and dependencies
- ✅ Create Python virtual environment
- ✅ Install Python dependencies from `requirements.txt`
- ✅ Create systemd service file at `/etc/systemd/system/cycle-tracker.service`
- ✅ Display next steps

### 3. Enable Auto-Start on Boot

```bash
# Enable service to start on boot
sudo systemctl enable cycle-tracker

# Start service now (optional)
sudo systemctl start cycle-tracker
```

### 4. Verify Installation

```bash
# Check service status
sudo systemctl status cycle-tracker

# View live logs
journalctl -u cycle-tracker -f

# Stop service (if needed)
sudo systemctl stop cycle-tracker
```

---

## First Run

### Initial Calibration

1. **Connect webcam and HDMI monitor to Pi**

2. **Start the application:**
   - If auto-start enabled: app starts on boot
   - If manual start: `sudo systemctl start cycle-tracker`

3. **Calibration mode:**
   - Application displays live video on HDMI monitor
   - ROI box overlays on feed
   - Message: "CALIBRATION MODE - Press S to save master"

4. **Position object in ROI:**
   - Place product/part in front of camera
   - Ensure ROI box fully captures the object
   - Press **S** to capture master silhouette

5. **Detection loop begins:**
   - Tabs auto-swap every 5 seconds
   - Tab 1: Live feed + real-time cycle timing
   - Tab 2: Shift summary with piece counts

---

## Configuration

Edit `config.yaml` to tune behavior:

```yaml
# Camera settings
camera_index: 0              # USB device (0 = first, check with v4l2-ctl -d /dev/video0 --list-formats-ext)
camera_width: 640            # Resolution (cap at 640×480 if USB bandwidth limited)
camera_height: 480
target_fps: 30

# ROI (Region of Interest) in pixels
roi:
  x: 200
  y: 150
  w: 240
  h: 180

# Detection tuning
canny_low: 50                # Edge detection sensitivity (lower = more edges)
canny_high: 150
match_threshold: 10          # Hamming distance (0=identical, higher=more tolerant)
confirm_frames: 5            # Debounce: consecutive frames to confirm PRESENT
absent_frames: 10            # Debounce: consecutive frames to confirm ABSENT
min_cycle_seconds: 2.0       # Reject cycles faster than this (bounce filter)

# Display
display_fullscreen: true
tab_swap_seconds: 5          # Auto-swap interval
result_hold_seconds: 2       # Flash duration for cycle result

# Rolling stats window
stats_window: 20             # Min/Avg/Max computed over last N cycles

# Shift times
shifts:
  DAY:     { start: "08:00", end: "16:00" }
  EVENING: { start: "16:00", end: "24:00" }
  NIGHT:   { start: "00:00", end: "08:00" }
```

### Tuning Tips

If detection isn't working well:

| Problem | Adjustment |
|---------|------------|
| Objects not detected | Lower `canny_low` or `match_threshold` |
| False positives (noise) | Raise `canny_low` or `match_threshold` |
| Flickering state changes | Increase `confirm_frames` or `absent_frames` |
| Cycle times inconsistent | Check lighting; increase `min_cycle_seconds` if bouncing |
| USB camera lag | Reduce `camera_width/height` or `target_fps` |

---

## File Locations

After installation:

```
/home/pi/cycle_time_tracking/
├── main.py
├── config.yaml              ← Edit to tune
├── venv/                    ← Virtual environment
├── today.json               ← Daily totals (created at runtime)
├── master.pkl               ← Master image (created after calibration)
├── history/                 ← Daily archives (YYYY-MM-DD.json)
└── logs/                    ← Optional (add if needed)
```

---

## Service Management

### Start / Stop / Restart

```bash
# Start service
sudo systemctl start cycle-tracker

# Stop service
sudo systemctl stop cycle-tracker

# Restart service (apply config changes)
sudo systemctl restart cycle-tracker

# Check status
sudo systemctl status cycle-tracker

# Disable auto-start (keep installed, don't auto-boot)
sudo systemctl disable cycle-tracker

# Re-enable auto-start
sudo systemctl enable cycle-tracker
```

### View Logs

```bash
# Live tail (last 50 lines + new output)
journalctl -u cycle-tracker -f

# Last 100 lines
journalctl -u cycle-tracker -n 100

# Since boot
journalctl -u cycle-tracker --since today

# Errors only
journalctl -u cycle-tracker | grep -i error
```

### Manual Start (for debugging)

```bash
# Activate venv and run directly
cd ~/cycle_time_tracking
source venv/bin/activate
python main.py

# Quit with Ctrl+C
```

---

## Troubleshooting

### Service Fails to Start

```bash
# Check for errors
sudo systemctl status cycle-tracker
journalctl -u cycle-tracker -n 20

# Common issues:
# - Camera not found: check USB connection, run: ls /dev/video*
# - Permission denied: check file ownership, run: sudo chown -R pi:pi ~/cycle_time_tracking
# - Port already in use: check if another instance running
```

### Camera Not Found

```bash
# List connected cameras
ls /dev/video*

# Get camera details
v4l2-ctl -d /dev/video0 --list-formats-ext

# Adjust camera_index in config.yaml (0 = first, 1 = second, etc.)
```

### Display Issues

```bash
# Check HDMI connection
xrandr  # (requires X server)

# Force fullscreen mode in config.yaml
display_fullscreen: true

# Restart service to apply
sudo systemctl restart cycle-tracker
```

### High CPU Usage

- Reduce `target_fps` (e.g., 15 instead of 30)
- Reduce `camera_width/height` (e.g., 480×360)
- Check for runaway processes: `top -p $(pidof python)`

### No Data Recorded

- Check `/home/pi/cycle_time_tracking/today.json` exists and has content
- Verify shift times in config.yaml match current time
- Check that cycles are actually detected (look at console logs)

---

## Maintenance

### Daily Backup (Optional)

```bash
# Backup today's data
cp ~/cycle_time_tracking/today.json ~/cycle_time_tracking/backups/today_$(date +%Y%m%d).json

# Schedule via cron (add to crontab)
0 23 * * * cp /home/pi/cycle_time_tracking/today.json /home/pi/cycle_time_tracking/backups/today_$(date +\%Y\%m\%d).json
```

### Update Configuration Without Restarting

1. Edit `config.yaml`
2. Restart service: `sudo systemctl restart cycle-tracker`

### Reinstall / Update Dependencies

```bash
cd ~/cycle_time_tracking
source venv/bin/activate
pip install --upgrade -r requirements.txt
sudo systemctl restart cycle-tracker
```

---

## Uninstall

```bash
# Stop and disable service
sudo systemctl stop cycle-tracker
sudo systemctl disable cycle-tracker

# Remove service file
sudo rm /etc/systemd/system/cycle-tracker.service
sudo systemctl daemon-reload

# Remove application (optional)
rm -rf ~/cycle_time_tracking
```

---

## Support

For issues or questions:
1. Check logs: `journalctl -u cycle-tracker -f`
2. Review [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
3. Test manually: `cd ~/cycle_time_tracking && source venv/bin/activate && python main.py`
