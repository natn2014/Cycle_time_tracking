# Installation Troubleshooting Guide

Quick fixes for common issues during Raspberry Pi setup.

---

## Package Installation Errors

### Error: "Unable to locate package libwebp6" or "libiff5"

**Cause:** Package names or availability varies between Raspberry Pi OS versions.

**Solution:**

```bash
# Use minimal install script instead (more reliable)
cd ~/cycle_time_tracking
chmod +x install_minimal.sh
./install_minimal.sh
```

Or manually install only what's needed:

```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-opencv python3-venv
cd ~/cycle_time_tracking
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Python / pip Errors

### Error: "No module named 'cv2'"

**Cause:** OpenCV not installed or installed in wrong Python environment.

**Solution:**

```bash
# Ensure venv is activated
source ~/cycle_time_tracking/venv/bin/activate

# Verify OpenCV
python -c "import cv2; print(cv2.__version__)"

# If still missing, install via pip
pip install opencv-python
```

### Error: "pip: command not found"

**Cause:** Python3-pip not installed.

**Solution:**

```bash
sudo apt-get install -y python3-pip
python3 -m pip --version  # Verify
```

---

## Virtual Environment Issues

### Error: "venv: command not found"

**Cause:** python3-venv not installed.

**Solution:**

```bash
sudo apt-get install -y python3-venv
python3 -m venv ~/cycle_time_tracking/venv
```

### Error: "activate: No such file"

**Cause:** venv not created or path wrong.

**Solution:**

```bash
cd ~/cycle_time_tracking
python3 -m venv venv
source venv/bin/activate

# Verify
python --version  # Should show Python 3.x
which python      # Should show /home/pi/cycle_time_tracking/venv/bin/python
```

---

## Systemd Service Issues

### Error: "Failed to enable unit: Unit file does not exist"

**Cause:** Service file not installed.

**Solution:**

```bash
# Manually copy and install service
sudo cp ~/cycle_time_tracking/cycle-tracker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable cycle-tracker
sudo systemctl status cycle-tracker
```

### Error: "Service StartLimitHit"

**Cause:** Service crashed or exited repeatedly.

**Solution:**

```bash
# Check what went wrong
journalctl -u cycle-tracker -n 50

# Common issues:
# 1. Config file missing or malformed
# 2. Camera not found
# 3. Permission denied

# Try manual run to see error
cd ~/cycle_time_tracking
source venv/bin/activate
python main.py
```

### Error: "Permission denied"

**Cause:** File ownership issue.

**Solution:**

```bash
# Fix ownership
sudo chown -R pi:pi ~/cycle_time_tracking

# Or fix service user (edit cycle-tracker.service)
sudo nano /etc/systemd/system/cycle-tracker.service
# Change: User=pi

sudo systemctl daemon-reload
sudo systemctl restart cycle-tracker
```

---

## Camera Issues

### Error: "Failed to read frame" or No video capture

**Cause:** Camera not found or wrong device index.

**Solution:**

```bash
# Check connected cameras
ls -la /dev/video*

# List available cameras with details
v4l2-ctl --list-devices

# If no /dev/video0, check USB connection
lsusb | grep -i camera

# Update camera_index in config.yaml if needed
nano ~/cycle_time_tracking/config.yaml
# Change: camera_index: 0  (or 1, 2, etc.)
```

### Error: "USB camera freezes or drops frames"

**Cause:** Camera resolution too high or FPS too high.

**Solution:**

```bash
# Edit config.yaml
nano ~/cycle_time_tracking/config.yaml

# Reduce resolution
camera_width: 480      # From 640
camera_height: 360     # From 480

# Reduce FPS
target_fps: 15         # From 30

# Restart
sudo systemctl restart cycle-tracker
```

---

## Disk Space Issues

### Error: "No space left on device"

**Cause:** RPi storage full.

**Solution:**

```bash
# Check disk usage
df -h

# Clean up old logs
journalctl --vacuum=100M

# Clean apt cache
sudo apt-get clean

# Check if today.json is huge (shouldn't be)
ls -lh ~/cycle_time_tracking/today.json
```

---

## Python Package Version Conflicts

### Error: "ModuleNotFoundError: No module named 'imagehash'"

**Cause:** Requirements not installed.

**Solution:**

```bash
source ~/cycle_time_tracking/venv/bin/activate
pip install -r ~/cycle_time_tracking/requirements.txt

# Verify installation
python -c "import imagehash; print('✓ imagehash OK')"
python -c "import cv2; print('✓ cv2 OK')"
python -c "import yaml; print('✓ yaml OK')"
```

---

## Display Issues

### Error: "Cannot open display" or "No module named 'Xlib'"

**Cause:** Running headless or X server not available.

**Solution:**

For systemd service (headless), this is normal. OpenCV uses internal frame buffer.

For manual testing, ensure HDMI is connected:

```bash
# Test if display works
DISPLAY=:0 python main.py

# Or run directly (should auto-detect display)
python main.py
```

---

## Network / SSH Issues

### Error: "Connection refused" (SSH)

**Cause:** RPi not on network or SSH not enabled.

**Solution:**

```bash
# Check if RPi is reachable
ping raspberrypi.local

# Enable SSH on RPi (run on RPi terminal or via Raspberry Pi Imager):
sudo systemctl enable ssh
sudo systemctl start ssh

# From PC, try again
ssh pi@raspberrypi.local
```

### Error: "Permission denied (publickey)"

**Cause:** SSH key not set up.

**Solution:**

Use password authentication:

```bash
ssh -o PubkeyAuthentication=no pi@raspberrypi.local
# Password: raspberry (default)
```

Or set up SSH keys:

```bash
ssh-keygen -t rsa
ssh-copy-id pi@raspberrypi.local
```

---

## Still Not Working?

### Step 1: Verify Installation
```bash
cd ~/cycle_time_tracking
source venv/bin/activate

# Test each module
python -c "from detector import FrameDetector; print('✓ detector')"
python -c "from state_machine import StateMachine; print('✓ state_machine')"
python -c "from shift_tracker import ShiftTracker; print('✓ shift_tracker')"
```

### Step 2: Test Manual Run
```bash
cd ~/cycle_time_tracking
source venv/bin/activate
python main.py

# Look at console output for errors
# Press Q to quit
```

### Step 3: Check Service Logs
```bash
# Last 50 lines
journalctl -u cycle-tracker -n 50

# Follow live logs
journalctl -u cycle-tracker -f

# All logs since boot
journalctl -u cycle-tracker --since today
```

### Step 4: Reinstall
```bash
# Full clean reinstall
rm -rf ~/cycle_time_tracking/venv
cd ~/cycle_time_tracking
chmod +x install_minimal.sh
./install_minimal.sh
```

---

## Getting Help

If still stuck:

1. **Run tests locally** (on development machine):
   ```bash
   python -m pytest test_*.py -v
   ```
   If tests pass on dev machine but fail on RPi, it's environment-specific.

2. **Check [DEPLOYMENT.md](DEPLOYMENT.md)** for detailed setup instructions.

3. **Review config.yaml** for obvious errors (YAML syntax, camera_index, etc.).

4. **Capture full error log**:
   ```bash
   journalctl -u cycle-tracker --since today > error_log.txt
   # Share this log for debugging
   ```

---

## Quick Recovery

If systemd service is broken, manually run:

```bash
# Activate venv
cd ~/cycle_time_tracking
source venv/bin/activate

# Run app directly (see all errors)
python main.py

# Once working, set up systemd again
sudo cp cycle-tracker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable cycle-tracker
sudo systemctl start cycle-tracker
```

---

*Last updated: 2026-07-01*
