# Quick Start Guide - 5 Minutes to Production

## On Your VPS

### Step 1: Install Docker & Python (2 minutes)

```bash
sudo apt-get update && sudo apt-get install -y docker.io python3 python3-pip chromium-browser
sudo systemctl start docker
sudo usermod -aG docker $USER
newgrp docker
```

### Step 2: Copy Script & Dependencies (1 minute)

```bash
cd /path/to/reddit-register-vps
pip3 install -r requirements.txt
chmod +x register.py run.sh stop.sh
```

### Step 3: Configure Credentials (1 minute)

Edit `config.json`:

```bash
nano config.json
```

Update these fields:
- `openvpn_user`: Your NordVPN email
- `openvpn_password`: Your NordVPN password

Save (Ctrl+X, Y, Enter)

### Step 4: Test & Run (1 minute)

**Test single instance:**

```bash
python3 register.py --instance 1
```

**Run 2 instances (parallel):**

```bash
./run.sh 2
```

**View logs:**

```bash
tail -f logs/register_instance_1.log
```

**Stop all:**

```bash
./stop.sh
```

## Key Files

| File | Purpose |
|------|---------|
| `register.py` | Main script (run with `--instance N`) |
| `run.sh` | Start multiple instances at once |
| `stop.sh` | Stop all instances |
| `config.json` | VPN credentials (EDIT THIS) |
| `logs/` | Instance logs |
| `data/registration_success.txt` | Registered accounts |

## Multi-Instance Mode

```bash
# Run 3 instances
./run.sh 3

# Each gets its own:
# - Container: gluetun_register_1, gluetun_register_2, gluetun_register_3
# - Port: 8888, 8988, 9088
# - Log: logs/register_instance_1.log, etc.
```

## Common Tasks

| Task | Command |
|------|---------|
| Start 2 instances | `./run.sh 2` |
| Start 5 instances | `./run.sh 5` |
| Stop all | `./stop.sh` |
| View instance 1 log | `tail -f logs/register_instance_1.log` |
| Count accounts | `wc -l data/registration_success.txt` |
| Check memory | `docker stats --no-stream` |
| List containers | `docker ps \| grep gluetun` |
| View IP being used | `curl -x http://127.0.0.1:8888 http://ipinfo.io/ip` |

## Troubleshooting

### "Docker permission denied"
```bash
sudo usermod -aG docker $USER
newgrp docker
```

### "Port 8888 in use"
```bash
# Kill process on port 8888
sudo lsof -i :8888 | awk 'NR!=1 {print $2}' | xargs kill -9
```

### "Chromium not found"
```bash
sudo apt-get install chromium-browser
```

### "NordVPN connection failed"
- Check credentials in `config.json`
- Test NordVPN manually on your machine first
- Ensure Docker can access internet

## VPS Sizing Recommendations

| Instances | vCPU | RAM | Speed |
|-----------|------|-----|-------|
| 1 | 1 | 2GB | 1 account/min |
| 2 | 2 | 4GB | 2 accounts/min |
| 3 | 4 | 8GB | 3 accounts/min |

Each instance needs: ~500MB RAM + browser ~1GB = ~1.5GB per instance.

## Next Steps

1. **Monitor**: `tail -f logs/register_instance_1.log`
2. **Scale**: Add more instances with `./run.sh N`
3. **Automate**: Use cron to restart on failure
4. **Collect**: Accounts saved in `data/registration_success.txt`

---

**Need help?** Check README.md for detailed documentation.
