# Reddit Account Registration - Standalone VPS Edition

Standalone Python script for bulk Reddit account registration on a VPS with **multi-instance support**. Each instance runs its own gluetun VPN proxy container for unique IP rotation.

## Features

- ✅ Standalone script (no Docker Compose needed)
- ✅ Multi-instance support (run 2+ instances simultaneously on same VPS)
- ✅ Each instance gets its own gluetun proxy container
- ✅ Automatic port allocation (8888, 8988, 9088, etc.)
- ✅ Browser fingerprinting (timezone, geolocation, viewport randomization)
- ✅ Automatic proxy restart on connection failures
- ✅ Detailed logging per instance
- ✅ Graceful account data export

## Prerequisites

### VPS Requirements

- Linux (Ubuntu 20.04+, Debian 11+, etc.)
- 4+ GB RAM per instance
- 10+ GB disk space
- Docker installed
- Python 3.10+
- Chromium/Chrome browser

### Setup Steps

#### 1. Install Dependencies

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3 python3-pip docker.io chromium-browser

# Verify installations
python3 --version
docker --version
which chromium-browser
```

#### 2. Install Python Dependencies

```bash
cd /path/to/reddit-register-vps
pip3 install -r requirements.txt
```

#### 3. Configure Credentials

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

#### 4. Prepare Script for Execution

```bash
chmod +x register.py run.sh stop.sh
```

#### 5. Test Single Instance

```bash
python3 register.py --instance 1
```

You should see:
```
[INFO] Reddit Account Registration Service - Instance 1
[INFO] Starting gluetun container...
[INFO] Using container: gluetun_register_1
[INFO] HTTP Proxy: http://127.0.0.1:8888
[INFO] Getting IP geolocation...
[INFO] IP: XX.XX.XX.XX
...
```

## Usage

### Single Instance

Run a single registration instance:

```bash
python3 register.py --instance 1
```

Log file: `logs/register_instance_1.log`

### Multiple Instances

Run 3 instances simultaneously:

```bash
./run.sh 3
```

This will:
- Start instance 1 (port 8888, container: gluetun_register_1)
- Start instance 2 (port 8988, container: gluetun_register_2)
- Start instance 3 (port 9088, container: gluetun_register_3)

Each runs in background. Monitor progress:

```bash
# View logs
tail -f logs/register_instance_1.log
tail -f logs/register_instance_2.log

# View output
cat logs/instance_1.out
```

### Stop Instances

```bash
./stop.sh
```

Or manually:

```bash
# Kill specific instance
kill <PID>

# Kill all register.py instances
pkill -f "python3.*register.py"
```

## Port Allocation

Each instance automatically allocates ports:

- **Instance 1**: Port 8888 (gluetun_register_1)
- **Instance 2**: Port 8988 (gluetun_register_2)
- **Instance 3**: Port 9088 (gluetun_register_3)
- **Instance N**: Port `8888 + (N-1)*100`

If port is unavailable, the script automatically finds the next available port.

## Output Files

```
reddit-register-vps/
├── logs/
│   ├── register_instance_1.log      # Main log for instance 1
│   ├── register_instance_2.log      # Main log for instance 2
│   ├── instance_1.out               # Startup output for instance 1
│   └── instance_2.out               # Startup output for instance 2
├── data/
│   └── registration_success.txt     # All registered accounts (CSV format)
├── config.json                       # VPN credentials
├── register.py                       # Main script
├── run.sh                           # Multi-instance launcher
├── stop.sh                          # Stop all instances
└── README.md                         # This file
```

### registration_success.txt Format

```
username,email,password,city,ip,instance
sarah_a1b2,sarah_a1b2@gmail.com,13123244,Dublin,1.2.3.4,1
mia_c3d4,mia_c3d4@gmail.com,13123244,London,5.6.7.8,2
bella_e5f6,bella_e5f6@gmail.com,13123244,Berlin,9.10.11.12,3
```

## Troubleshooting

### Port Already in Use

```
[ERROR] Could not find available port starting from 8888
```

**Solution**: Kill processes on those ports or use different instance numbers:

```bash
sudo netstat -tlnp | grep 8888
sudo kill -9 <PID>
```

### Docker Permission Denied

```
[ERROR] Failed to connect to Docker: permission denied
```

**Solution**: Add user to docker group:

```bash
sudo usermod -aG docker $USER
newgrp docker
```

### Chromium Not Found

```
[DEBUG] No Chromium executable found
```

**Solution**: Install Chromium:

```bash
sudo apt-get install chromium-browser
# or
sudo apt-get install google-chrome-stable
```

### Gluetun Container Won't Start

```
[ERROR] Error starting gluetun container: ...
```

**Check**:
1. NordVPN credentials are correct in `config.json`
2. Docker daemon is running: `sudo systemctl start docker`
3. Sufficient disk space: `df -h`
4. Docker image exists: `docker pull qmcgaw/gluetun:latest`

### Proxy Connection Timeouts

If you see repeated "Tunnel connection failed: 503" errors:

1. Check internet connectivity on VPS
2. Restart container manually:
   ```bash
   docker restart gluetun_register_1
   ```
3. Check NordVPN status (may be rate-limited)

### Account Registration Always Fails

Check:
1. Proxy is working: `curl -x http://127.0.0.1:8888 http://ipinfo.io/ip`
2. Reddit site is accessible
3. Browser has access to /tmp (Zendriver cache)
4. Sufficient memory: `free -h`

## Performance Tips

### CPU/Memory per Instance

- **Min**: 1 vCPU + 2GB RAM
- **Recommended**: 2 vCPU + 4GB RAM
- **Optimal**: 4 vCPU + 8GB RAM

### For 3 Instances on 8GB VPS

```bash
# Start 3 instances with spacing
./run.sh 3
```

Monitor memory:

```bash
watch -n 1 'free -h && echo "---" && docker stats --no-stream'
```

### Increase Registration Rate

Adjust delays in `register.py` (lines with `await asyncio.sleep()`):

```python
# Reduce these values for faster registration
await asyncio.sleep(random.uniform(0.5, 1.0))  # → 0.2 to 0.5
await asyncio.sleep(3)  # → 1
```

## Monitoring

### Watch Live Progress

```bash
# Instance 1
tail -f logs/register_instance_1.log | grep -E "\[SUCCESS\]|\[FAILED\]|\[ERROR\]"

# All instances
tail -f logs/*.log
```

### Count Successful Registrations

```bash
wc -l data/registration_success.txt
```

### Check Running Instances

```bash
ps aux | grep "python3.*register.py"
docker ps | grep gluetun_register
```

## Advanced: Custom VPN Locations

Edit `config.json` to use specific VPN server:

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

Restart instances for changes to take effect.

## Support for Other VPN Providers

Modify `config.json`:

```json
{
  "gluetun": {
    "vpn_service_provider": "expressvpn",
    "openvpn_user": "...",
    "openvpn_password": "..."
  }
}
```

Supported providers: `nordvpn`, `expressvpn`, `surfshark`, `windscribe`, `purevpn`, `cyberghost`

## License

This tool is provided as-is for educational purposes.

## Notes

- Always respect Reddit's Terms of Service
- Rotate IPs appropriately to avoid detection
- Use realistic account behavior
- Monitor and log all activity
- Comply with local laws regarding automation
# RedditMassAccountCreator
# RedditMassAccountCreator
