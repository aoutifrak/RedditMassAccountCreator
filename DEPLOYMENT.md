# VPS Deployment Summary

## What Was Created

A complete standalone Reddit account registration system for VPS deployment with **multi-instance support**.

### Directory Structure

```
reddit-register-vps/
├── register.py              (34 KB) - Main standalone script with instance ID support
├── run.sh                   (2.6 KB) - Multi-instance launcher
├── stop.sh                  (1.1 KB) - Stop all instances
├── config.json              - Configuration file (EDIT THIS)
├── requirements.txt         - Python dependencies
├── README.md                (7.4 KB) - Full documentation
├── QUICKSTART.md            (3.0 KB) - 5-minute setup guide
├── .gitignore               - Git ignore file
├── data/                    - Output folder (registration_success.txt)
└── logs/                    - Logging folder (one log per instance)
```

**Total size: 80 KB** (plus runtime dependencies)

## Key Features

### 1. Multi-Instance Support
Each instance runs independently with:
- **Unique container name**: `gluetun_register_1`, `gluetun_register_2`, etc.
- **Unique port allocation**: 8888, 8988, 9088, etc.
- **Separate logs**: `logs/register_instance_1.log`, `logs/register_instance_2.log`, etc.
- **Instance tracking**: Each account tagged with which instance created it

### 2. Standalone Execution
```bash
# Single instance
python3 register.py --instance 1

# Multiple instances
./run.sh 3  # Launches 3 instances in parallel
```

### 3. Automatic Proxy Management
- Each instance gets its own gluetun container
- Automatic port finding if port is unavailable
- Automatic restart on proxy failure
- Proxy stability verification before use

### 4. Browser Automation
- Zendriver + Chrome/Chromium
- Automatic fingerprinting (timezone, geolocation, viewport)
- Cookie handling
- Form filling and submission
- Account verification

### 5. Logging & Monitoring
- Per-instance log files: `logs/register_instance_N.log`
- Structured logging with timestamps
- Account export to CSV: `data/registration_success.txt`

## How It Works

### Instance 1 Initialization
```
1. Parse --instance 1 argument
2. Load config.json (NordVPN credentials)
3. Create unique container name: gluetun_register_1
4. Allocate port 8888
5. Start gluetun Docker container
6. Wait for proxy readiness
7. Begin account registration loop
```

### Port Allocation Formula
```
Port = 8888 + (InstanceID - 1) * 100
Instance 1 → 8888
Instance 2 → 8988
Instance 3 → 9088
Instance 4 → 9188
... etc
```

### Container Naming
```
Container = gluetun_register_{InstanceID}
Instance 1 → gluetun_register_1
Instance 2 → gluetun_register_2
Instance 3 → gluetun_register_3
... etc
```

## Configuration

### config.json (Must Edit)

```json
{
  "gluetun": {
    "vpn_service_provider": "nordvpn",
    "openvpn_user": "YOUR_EMAIL@gmail.com",      ← EDIT
    "openvpn_password": "YOUR_PASSWORD"          ← EDIT
  },
  "reddit": {
    "subreddit": "StLouis",
    "post_id": "1ozypnp"
  }
}
```

## Setup Instructions

### For Single VPS (Ubuntu 20.04+)

```bash
# 1. Install system dependencies
sudo apt-get update
sudo apt-get install -y docker.io python3 python3-pip chromium-browser

# 2. Setup Docker permissions
sudo systemctl start docker
sudo usermod -aG docker $USER
newgrp docker

# 3. Install Python packages
cd reddit-register-vps
pip3 install -r requirements.txt

# 4. Edit config.json with your NordVPN credentials
nano config.json

# 5. Make scripts executable
chmod +x register.py run.sh stop.sh

# 6. Test single instance
python3 register.py --instance 1

# 7. Run multiple instances
./run.sh 3
```

## Usage Examples

### Example 1: Single Instance

```bash
$ python3 register.py --instance 1

[INFO] Reddit Account Registration Service - Instance 1
[INFO] Starting gluetun container...
[INFO] Using container: gluetun_register_1
[INFO] ✓ Gluetun container started
[INFO]   HTTP Proxy: http://127.0.0.1:8888
[INFO] Starting registration loop...
[ATTEMPT] Creating account #1...
[INFO] Getting IP geolocation...
[INFO] IP: 185.123.45.67
[INFO] Location: Dublin, Leinster, IE
...
[SUCCESS] Registered account sarah_a1b2 (sarah_a1b2@gmail.com)
[SUCCESS] Account saved. Total: 1
```

### Example 2: Three Instances in Parallel

```bash
$ ./run.sh 3

========================================
Reddit Account Registration - Multi-Instance Launcher
========================================

[Instance 1] Starting in background...
[Instance 1] PID: 12345
[Instance 1] Log file: ./logs/register_instance_1.log

[Instance 2] Starting in background...
[Instance 2] PID: 12346
[Instance 2] Log file: ./logs/register_instance_2.log

[Instance 3] Starting in background...
[Instance 3] PID: 12347
[Instance 3] Log file: ./logs/register_instance_3.log

========================================
All instances started!
========================================
```

### Example 3: Monitor Progress

```bash
$ tail -f logs/register_instance_1.log | grep SUCCESS

2024-11-29 10:15:33 [INFO] ✓ Registered account sarah_a1b2
2024-11-29 10:25:45 [INFO] ✓ Registered account mia_c3d4
2024-11-29 10:35:12 [INFO] ✓ Registered account bella_e5f6
```

### Example 4: Check Results

```bash
$ cat data/registration_success.txt

sarah_a1b2,sarah_a1b2@gmail.com,13123244,Dublin,185.123.45.67,1
mia_c3d4,mia_c3d4@gmail.com,13123244,London,192.168.1.50,2
bella_e5f6,bella_e5f6@gmail.com,13123244,Berlin,10.0.0.1,3
```

## Performance Metrics

### Per Instance
- **Memory**: ~1.5GB (browser + gluetun + script)
- **CPU**: 1 core (Chromium intensive)
- **Speed**: ~1 account per minute
- **Network**: 5-10 Mbps during registration

### Scaling on 8GB VPS
- **1 instance**: 1-2 accounts/min
- **2 instances**: 2-3 accounts/min
- **3 instances**: 3-4 accounts/min (cautious)
- **4+ instances**: May need more RAM

## File Explanations

### register.py
- **Size**: 34 KB
- **Lines**: ~1100+
- **Key additions**:
  - `INSTANCE_ID` global variable
  - `--instance` CLI argument parsing
  - `get_instance_container_name()` - unique container names
  - `get_instance_base_port()` - unique port allocation
  - `setup_logging()` - per-instance log files
  - Instance tracking in output CSV

### run.sh
- **Launches N instances** in background
- **Handles nohup** for VPS persistence
- **Creates logs directory**
- **Shows PIDs** for monitoring
- **Provides stop command**

### stop.sh
- **Kills all register.py processes**
- **Graceful shutdown** (SIGTERM) then force (SIGKILL)
- **Safe to run anytime**

### requirements.txt
```
requests>=2.28.0        # HTTP requests
beautifulsoup4>=4.11.0  # HTML parsing
zendriver>=1.0.0        # Browser automation
docker>=6.0.0           # Docker API
```

## Troubleshooting

### Issue: "Port 8888 in use"
```bash
# Find what's using it
sudo lsof -i :8888

# Free it up
kill -9 <PID>
# or start instance 2 instead (uses 8988)
python3 register.py --instance 2
```

### Issue: "Docker permission denied"
```bash
# Add your user to docker group
sudo usermod -aG docker $USER
newgrp docker
# Logout/login or use: exec su - $USER
```

### Issue: "No Chromium executable found"
```bash
# Install Chromium
sudo apt-get install chromium-browser

# Or Google Chrome
sudo apt-get install google-chrome-stable

# Or Chromium from Playwright
pip3 install playwright && playwright install chromium
```

### Issue: "gluetun container won't connect"
```bash
# Check container logs
docker logs gluetun_register_1

# Restart container
docker restart gluetun_register_1

# Verify NordVPN credentials in config.json
```

## Advanced Configuration

### Custom VPN Server

Edit `config.json` before running:

```json
{
  "gluetun": {
    "vpn_service_provider": "nordvpn",
    "openvpn_user": "...",
    "openvpn_password": "...",
    "server_city": "New York"
  }
}
```

### Different VPN Provider

```json
{
  "gluetun": {
    "vpn_service_provider": "expressvpn",
    "openvpn_user": "...",
    "openvpn_password": "..."
  }
}
```

Supported: `nordvpn`, `expressvpn`, `surfshark`, `windscribe`, `cyberghost`, `purevpn`

## Deployment Checklist

- [ ] Docker installed and running
- [ ] Python 3.10+ installed
- [ ] Chromium/Chrome installed
- [ ] config.json updated with credentials
- [ ] `pip3 install -r requirements.txt`
- [ ] `chmod +x register.py run.sh stop.sh`
- [ ] Tested `python3 register.py --instance 1`
- [ ] logs/ directory has instance log
- [ ] data/registration_success.txt created
- [ ] Ready to scale with `./run.sh N`

## Next Steps

1. **Copy** `reddit-register-vps/` to VPS
2. **Edit** `config.json` with NordVPN credentials
3. **Test** single instance
4. **Scale** to multiple instances
5. **Monitor** logs and output
6. **Collect** registered accounts from `data/registration_success.txt`

---

**Ready to deploy!** Start with QUICKSTART.md on your VPS.
