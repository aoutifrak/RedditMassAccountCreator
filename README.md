# Reddit Account Registration - Camoufox Anti-Detection Edition

Standalone Python script for bulk Reddit account registration on a VPS with **multi-instance support**. Uses **Camoufox** (Firefox-based anti-detect browser) for superior bot detection evasion. Each instance runs its own gluetun VPN proxy container for unique IP rotation.

## Features

- ✅ **Camoufox anti-detect browser** (C++ level fingerprinting, undetectable by JavaScript)
- ✅ WebRTC IP spoofing at protocol level
- ✅ Tested passing: CreepJS, Cloudflare Turnstile, DataDome, Imperva, reCaptcha v3
- ✅ Standalone script (no Docker Compose needed)
- ✅ Multi-instance support (run 2+ instances simultaneously on same VPS)
- ✅ Each instance gets its own gluetun proxy container
- ✅ Automatic port allocation (8888, 8988, 9088, etc.)
- ✅ Browser fingerprinting (timezone, geolocation, viewport randomization)
- ✅ Image blocking for faster page loads
- ✅ Automatic proxy restart on connection failures
- ✅ Detailed logging per instance
- ✅ Graceful account data export

## Prerequisites

### VPS Requirements

- Linux (Ubuntu 20.04+, Debian 11+, etc.)
- 4+ GB RAM per instance
- 10+ GB disk space (Camoufox Firefox binary ~700MB + cache)
- Docker installed and running
- Python 3.10+
- No Chromium/Chrome needed (Camoufox provides Firefox)

## Installation

### Step 1: System Dependencies

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3 python3-pip docker.io

# Verify installations
python3 --version
docker --version
```

**Note**: Camoufox will automatically download Firefox (~700MB) on first run.

### Step 2: Python Dependencies

```bash
cd /home/kali/Desktop/project/reddit-register-vps
pip install -r requirements.txt
```

This installs:
- `camoufox[geoip]` - Anti-detect Firefox browser with geolocation
- `playwright` - Browser automation
- `beautifulsoup4` - HTML parsing
- `requests` - HTTP library
- `docker` - Container management

### Step 3: Docker Setup

Ensure Docker daemon is running:

```bash
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group (optional, to avoid sudo)
sudo usermod -aG docker $USER
newgrp docker
```

### Step 4: Configure Credentials

Edit `config.json` with your NordVPN credentials:

```bash
nano config.json
```

```json
{
  "gluetun": {
    "vpn_service_provider": "nordvpn",
    "openvpn_user": "your_nordvpn_email@example.com",
    "openvpn_password": "your_nordvpn_password"
  },
  "reddit": {
    "subreddit": "StLouis",
    "post_id": "1ozypnp"
  }
}
```

### Step 5: Test Installation

```bash
chmod +x camoufox.py run.sh stop.sh

# Test single instance
python3 camoufox.py --instance 1
```

Expected output:
```
[INFO] ============================================================
[INFO] Reddit Account Registration Service - Instance 1
[INFO] Using: Camoufox + Playwright (Anti-Detection)
[INFO] ============================================================
[INFO] ✓ Loaded config from ./config.json
[INFO] Using container: gluetun_register_1
[INFO] Starting gluetun container...
[INFO] ✓ Gluetun container started
[INFO] HTTP Proxy: http://127.0.0.1:8888
[INFO] Getting IP geolocation...
[INFO] IP: 1.2.3.4
[INFO] Location: Dublin, Leinster, IE
[INFO] Timezone: Europe/Dublin
[INFO] Starting Camoufox browser...
[INFO] Camoufox browser started (attempt 1)
[INFO] Navigating to Reddit...
```

## Usage

### Single Instance

```bash
python3 camoufox.py --instance 1
```

Monitor logs:
```bash
tail -f logs/camoufox_instance_1.log
```

### Multiple Instances

```bash
./run.sh 3
```

This launches 3 instances with unique proxies:
- **Instance 1**: Port 8888, Container `gluetun_register_1`
- **Instance 2**: Port 8988, Container `gluetun_register_2`
- **Instance 3**: Port 9088, Container `gluetun_register_3`

Monitor all instances:
```bash
tail -f logs/camoufox_instance_*.log
```

### Stop Instances

```bash
./stop.sh
```

Or manually:
```bash
# Kill specific instance
kill <PID>

# Kill all instances
pkill -f "python3.*camoufox.py"
```

## Output

### Successful Registration

```
[INFO] ✓ Email filled
[INFO] ✓ Continue button clicked (selector: button:has-text("Continue"))
[INFO] ✓ Username filled
[INFO] ✓ Password filled
[INFO] ✓ Sign up button clicked (selector: button:has-text("Sign Up"))
[INFO] ✓ Skipped bonus features
[INFO] Verifying account: bella_x1y2
[INFO] Account status: active
[INFO] ✓ Registered account bella_x1y2 (bella_x1y2@gmail.com)
```

### Accounts File

Registered accounts are saved to `data/registration_success.txt`:

```csv
username,email,password,city,ip,instance
bella_x1y2,bella_x1y2@gmail.com,13123244,Dublin,1.2.3.4,1
mia_c3d4,mia_c3d4@gmail.com,13123244,London,5.6.7.8,2
isabella_e5f6,isabella_e5f6@gmail.com,13123244,Berlin,9.10.11.12,3
```

## Anti-Detection Features

### Camoufox Built-in Protections

- **C++ Fingerprinting**: Undetectable by JavaScript inspectors
- **WebRTC IP Leak Prevention**: Real IP never exposed
- **Font Antifingerprinting**: Random font metrics per session
- **Mouse Movement**: Human-like cursor behavior
- **Ad Blocking**: Reduces tracking/detection vectors
- **CSS Animation Removal**: Faster rendering
- **Memory Efficient**: ~200MB vs 400MB+ for Chrome

### Tested Against

- ✅ CreepJS (browser detection)
- ✅ Cloudflare Turnstile
- ✅ DataDome bot detection
- ✅ Imperva WAF
- ✅ reCaptcha v3

## Port Allocation

Each instance automatically gets a unique port:

```
Instance 1: 8888  (8888 + (1-1)*100)
Instance 2: 8988  (8888 + (2-1)*100)
Instance 3: 9088  (8888 + (3-1)*100)
Instance N: 8888 + (N-1)*100
```

If a port is busy, the script finds the next available port.

## Troubleshooting

### Docker Permission Denied

```
[ERROR] Failed to connect to Docker: permission denied
```

**Solution**:
```bash
sudo usermod -aG docker $USER
newgrp docker
docker ps  # Verify
```

### Camoufox Download Fails

First run downloads Firefox (~700MB). If it fails:

```bash
# Check logs
tail -f logs/camoufox_instance_1.log | grep -i download

# Manual download
python3 -c "from camoufox import AsyncCamoufox; import asyncio; asyncio.run(AsyncCamoufox().start())"
```

### Gluetun Container Won't Start

```
[ERROR] Error starting gluetun container: ...
```

**Check**:
1. Docker daemon: `sudo systemctl start docker`
2. NordVPN credentials in `config.json`
3. Disk space: `df -h`
4. Docker image: `docker pull qmcgaw/gluetun:latest`

### Proxy Connection Timeouts

```
[ERROR] Proxy did not respond after X quick attempts
```

**Solutions**:
1. Check internet: `curl -I https://google.com`
2. Restart container: `docker restart gluetun_register_1`
3. Check NordVPN status (may be rate-limited)

### Continue Button Not Clicking

If form submission fails:

1. Check logs for selector errors:
   ```bash
   grep "Continue selector" logs/camoufox_instance_1.log
   ```

2. The script tries multiple selectors automatically
3. As last resort, presses Enter key on email field

### Account Verification Fails

If account created but marked as inactive:

```
[ERROR] Account not active, status: not_found
```

**Causes**:
- Reddit still processing account (5-10s delay)
- Proxy IP blocked
- Account banned immediately

**Solution**: Check manually after ~15 seconds:
```bash
curl -x http://127.0.0.1:8888 https://www.reddit.com/user/username_here
```

## Performance Optimization

### Memory per Instance

- **Minimum**: 1 vCPU + 2GB RAM
- **Recommended**: 2 vCPU + 4GB RAM
- **Optimal**: 4 vCPU + 8GB RAM

### Speed Up Registration

Edit `camoufox.py` to reduce delays:

```python
# Line ~670: Reduce sleep intervals
await asyncio.sleep(random.uniform(0.2, 0.5))  # Down from 0.5-1.0
```

### Monitor Resource Usage

```bash
# Watch memory/CPU
watch -n 1 'free -h && echo "---" && docker stats --no-stream'

# Count registered accounts
wc -l data/registration_success.txt
```

## Advanced Configuration

### Custom VPN Location

Edit `config.json`:

```json
{
  "gluetun": {
    "vpn_service_provider": "nordvpn",
    "openvpn_user": "...",
    "openvpn_password": "...",
    "server_city": "Dublin",
    "server_country": "IE"
  }
}
```

### Other VPN Providers

```json
{
  "gluetun": {
    "vpn_service_provider": "expressvpn",
    "openvpn_user": "...",
    "openvpn_password": "..."
  }
}
```

Supported: `nordvpn`, `expressvpn`, `surfshark`, `windscribe`, `purevpn`, `cyberghost`

## File Structure

```
reddit-register-vps/
├── camoufox.py                 # Main script (Camoufox-based)
├── config.json                 # VPN & Reddit config
├── requirements.txt            # Python dependencies
├── run.sh                       # Multi-instance launcher
├── stop.sh                      # Stop all instances
├── README.md                    # This file
├── logs/
│   ├── camoufox_instance_1.log
│   ├── camoufox_instance_2.log
│   ├── instance_1.out
│   └── instance_2.out
├── data/
│   └── registration_success.txt # Registered accounts (CSV)
└── ovpn_tcp/                    # NordVPN OVPN configs (optional)
    ├── be148.nordvpn.com.tcp.ovpn
    ├── pl128.nordvpn.com.tcp.ovpn
    └── us5067.nordvpn.com.tcp.ovpn
```

## Upgrade from Zendriver

The old `register.py` (zendriver-based) has been removed.

### Migration Checklist

- [x] Update Python dependencies: `pip install -r requirements.txt`
- [x] Use `camoufox.py` instead of `register.py`
- [x] Existing accounts in `data/registration_success.txt` still work
- [x] Log format changed to `logs/camoufox_instance_N.log`

## License

This tool is provided as-is for educational purposes.

## Notes

- Always respect Reddit's Terms of Service
- Rotate IPs appropriately
- Use realistic account behavior
- Monitor and log all activity
- Comply with local laws regarding automation
