# Setup Guide - Camoufox Edition

Complete setup instructions for Reddit Account Registration using Camoufox anti-detect browser.

## Prerequisites

### System Requirements

```bash
# Check Python version (must be 3.10+)
python3 --version

# Check Docker
docker --version
sudo systemctl status docker
```

### Installation Order

1. System dependencies
2. Python dependencies
3. Docker setup
4. Configuration
5. Test & verify

## Step 1: System Dependencies (5 minutes)

### Ubuntu/Debian

```bash
sudo apt-get update
sudo apt-get install -y \
    python3 \
    python3-pip \
    docker.io \
    curl \
    wget

# Verify
python3 --version  # >= 3.10
docker --version   # >= 20.10
pip3 --version
```

### Other Linux Distributions

Refer to your package manager. You need:
- Python 3.10+
- Docker 20.10+
- pip3

## Step 2: Python Dependencies (10 minutes)

### Create Virtual Environment (Recommended)

```bash
cd /home/kali/Desktop/project/reddit-register-vps

# Create venv
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### Install Requirements

```bash
# From requirements.txt
pip install -r requirements.txt
```

**Expected output**:
```
Collecting camoufox[geoip]>=0.4.11
  Downloading camoufox-0.4.11-py3-none-manylinux1_x86_64.whl (...)
  ...
Successfully installed camoufox-0.4.11 playwright-1.56.0 ...
```

### First-Time Camoufox Setup

Camoufox will download Firefox (~700MB) on first run:

```bash
# Test installation
python3 -c "from camoufox import AsyncCamoufox; print('✓ Camoufox imported')"

# Manual Firefox download (optional)
python3 << 'EOF'
import asyncio
from camoufox import AsyncCamoufox

async def setup():
    print("Downloading Firefox browser...")
    browser = await AsyncCamoufox().start()
    await browser.stop()
    print("✓ Firefox downloaded successfully")

asyncio.run(setup())
EOF
```

## Step 3: Docker Setup (5 minutes)

### Verify Docker Daemon

```bash
# Start Docker
sudo systemctl start docker

# Enable on boot
sudo systemctl enable docker

# Verify running
sudo systemctl status docker
```

### Docker Permissions (Optional)

To avoid using `sudo` for Docker commands:

```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker ps  # Should work without sudo
```

### Pull Gluetun Image

```bash
# Pre-pull image to avoid delays
docker pull qmcgaw/gluetun:latest

# Verify
docker images | grep gluetun
```

## Step 4: Configuration (5 minutes)

### Create config.json

```bash
nano config.json
```

### Minimal Configuration

```json
{
  "gluetun": {
    "vpn_service_provider": "nordvpn",
    "openvpn_user": "your_email@example.com",
    "openvpn_password": "your_password"
  },
  "reddit": {
    "subreddit": "StLouis",
    "post_id": "1ozypnp"
  }
}
```

### Full Configuration

```json
{
  "gluetun": {
    "vpn_service_provider": "nordvpn",
    "openvpn_user": "your_email@example.com",
    "openvpn_password": "your_password",
    "server_city": "Dublin",
    "server_country": "IE"
  },
  "reddit": {
    "subreddit": "StLouis",
    "post_id": "1ozypnp"
  }
}
```

### Save & Verify

```bash
# Verify JSON is valid
python3 -c "import json; json.load(open('config.json'))" && echo "✓ Valid JSON"
```

## Step 5: Permissions

```bash
chmod +x camoufox.py run.sh stop.sh

# Verify
ls -la camoufox.py run.sh stop.sh
```

## Step 6: Test Installation

### Single Instance Test

```bash
python3 camoufox.py --instance 1
```

**Expected sequence**:

1. Container starts (10-20s)
2. Proxy ready message
3. Geolocation obtained
4. Browser starts
5. Navigation to Reddit
6. Registration begins

**Success indicators**:
```
[INFO] ✓ Email filled
[INFO] ✓ Continue button clicked
[INFO] ✓ Username filled
[INFO] ✓ Password filled
[INFO] ✓ Sign up button clicked
[INFO] ✓ Registered account username (email@gmail.com)
```

### Stop Test Instance

```bash
# Press Ctrl+C to stop
```

Check logs:
```bash
tail -n 50 logs/camoufox_instance_1.log
```

## Step 7: Multi-Instance Setup (Optional)

### Launch Multiple Instances

```bash
./run.sh 3
```

### Monitor

```bash
# View all logs
tail -f logs/camoufox_instance_*.log

# Count instances
ps aux | grep "camoufox.py" | grep -v grep | wc -l
```

### Stop All

```bash
./stop.sh
# or
pkill -f "python3.*camoufox.py"
```

## Troubleshooting

### Python Version Mismatch

```
Error: Python 3.9 is not supported
```

**Solution**: Install Python 3.10+ or use pyenv:
```bash
# On Ubuntu 20.04
sudo apt-get install python3.11
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Docker Permission Issues

```
ERROR: permission denied while trying to connect to Docker daemon
```

**Solution**:
```bash
sudo usermod -aG docker $USER
newgrp docker
docker ps  # Verify
```

### Camoufox Download Fails

```
[ERROR] Failed to download Firefox
```

**Solutions**:
1. Check internet: `ping google.com`
2. Check disk space: `df -h` (need >1GB free)
3. Manual download:
   ```bash
   python3 << 'EOF'
   from camoufox import AsyncCamoufox
   import asyncio
   
   async def download():
       browser = await AsyncCamoufox().start()
       await browser.stop()
   
   asyncio.run(download())
   EOF
   ```

### Port Already in Use

```
[ERROR] Could not find available port starting from 8888
```

**Solution**:
```bash
# Find what's using the port
sudo netstat -tlnp | grep 8888

# Kill it
sudo kill -9 <PID>

# Or use different instance number
python3 camoufox.py --instance 5  # Uses port 9388
```

### Gluetun Won't Start

```
[ERROR] Error starting gluetun container
```

**Check**:
1. NordVPN credentials correct in `config.json`
2. Internet connection working
3. Docker service running: `sudo systemctl restart docker`
4. Disk space available: `df -h`

### Registration Always Fails

1. Check proxy: `curl -x http://127.0.0.1:8888 http://ipinfo.io/ip`
2. Check Reddit accessible: `curl https://www.reddit.com`
3. View logs: `tail -f logs/camoufox_instance_1.log`

## Verification Checklist

- [ ] Python 3.10+ installed
- [ ] Docker service running
- [ ] `config.json` created with valid JSON
- [ ] `camoufox.py`, `run.sh`, `stop.sh` are executable
- [ ] Single instance test successful
- [ ] Accounts saved to `data/registration_success.txt`

## Next Steps

1. **Read README.md** for usage details
2. **Run single instance** to verify setup
3. **Launch multi-instance** for bulk registration
4. **Monitor logs** with `tail -f logs/camoufox_instance_*.log`

## Support

For issues:
1. Check logs: `logs/camoufox_instance_N.log`
2. Review README.md troubleshooting section
3. Verify prerequisites are installed

## Quick Reference

```bash
# Activate venv
source venv/bin/activate

# Single instance
python3 camoufox.py --instance 1

# Multiple instances
./run.sh 3

# Stop all
./stop.sh

# View logs
tail -f logs/camoufox_instance_1.log

# Count accounts
wc -l data/registration_success.txt
```
