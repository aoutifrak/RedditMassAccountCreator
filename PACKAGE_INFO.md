# Reddit Account Registration VPS - Complete Package

## 📦 What You Get

A **turnkey standalone system** for running multi-instance Reddit account registration on any VPS.

### Location
```
/home/kali/Desktop/project/reddit-register-vps/
```

### File Manifest

```
reddit-register-vps/                    ← Main folder (80 KB)
│
├── 📄 QUICKSTART.md                    ← Start here! (5-min setup)
├── 📄 README.md                        ← Full documentation
├── 📄 DEPLOYMENT.md                    ← Reference guide
├── 📄 .gitignore                       ← Git configuration
│
├── ⚙️  register.py                     ← Main script (34 KB, ~1100 lines)
│                                         ✓ Multi-instance support
│                                         ✓ Auto port allocation
│                                         ✓ Proxy management
│                                         ✓ Browser automation
│                                         ✓ Account registration
│                                         ✓ Per-instance logging
│
├── 🚀 run.sh                          ← Launch N instances
│                                         Usage: ./run.sh 3
│
├── ⏹️  stop.sh                         ← Stop all instances
│                                         Usage: ./stop.sh
│
├── 📋 config.json                      ← Configuration (EDIT THIS!)
│                                         Set NordVPN credentials
│
├── 📦 requirements.txt                 ← Python dependencies
│                                         pip3 install -r requirements.txt
│
├── 📁 logs/                           ← Output logs (created at runtime)
│   ├── register_instance_1.log
│   ├── register_instance_2.log
│   └── instance_1.out
│
└── 📁 data/                           ← Registered accounts (created at runtime)
    └── registration_success.txt       ← CSV export (username, email, password, city, ip, instance)
```

## 🚀 Quick Start (Copy-Paste)

### On Your VPS

```bash
# 1. Install dependencies
sudo apt-get update && sudo apt-get install -y docker.io python3 python3-pip chromium-browser
sudo systemctl start docker
sudo usermod -aG docker $USER
newgrp docker

# 2. Clone/copy the folder
cd reddit-register-vps

# 3. Install Python packages
pip3 install -r requirements.txt

# 4. Edit configuration
nano config.json
# → Change openvpn_user and openvpn_password

# 5. Make executable
chmod +x register.py run.sh stop.sh

# 6. Test single instance
python3 register.py --instance 1

# 7. Run 3 instances in parallel
./run.sh 3

# 8. Monitor (from another terminal)
tail -f logs/register_instance_1.log
```

## 🎯 Key Differences from Original

| Feature | Original (services/register/) | VPS Standalone |
|---------|-------------------------------|-----------------|
| **Location** | Docker service in compose | Standalone VPS folder |
| **Execution** | Docker container | Native Python |
| **Multi-instance** | ❌ Not supported | ✅ Full support (`--instance N`) |
| **Container naming** | `register` (fixed) | `gluetun_register_1`, `gluetun_register_2`, etc. |
| **Port allocation** | Fixed in docker-compose | Auto-allocated per instance |
| **Logging** | Shared `/shared/accounts/` | Per-instance files in `logs/` |
| **Config** | Inside Dockerfile | External `config.json` |
| **Dependencies** | Docker image | Python packages only |
| **Setup time** | 10+ mins (build) | ~2 mins |

## 💡 Multi-Instance Architecture

Each instance runs independently:

```
VPS (8GB RAM, 4 vCPU)
│
├─ Instance 1 (Python process, PID: 12345)
│  ├─ gluetun_register_1 (Docker container, port 8888)
│  ├─ Chromium browser process
│  └─ logs/register_instance_1.log
│
├─ Instance 2 (Python process, PID: 12346)
│  ├─ gluetun_register_2 (Docker container, port 8988)
│  ├─ Chromium browser process
│  └─ logs/register_instance_2.log
│
└─ Instance 3 (Python process, PID: 12347)
   ├─ gluetun_register_3 (Docker container, port 9088)
   ├─ Chromium browser process
   └─ logs/register_instance_3.log

Shared: data/registration_success.txt (all accounts from all instances)
```

## 📊 Performance Expectations

### Single VPS (8GB RAM)

| Setup | Instances | Accounts/Min | Memory | CPU |
|-------|-----------|-------------|--------|-----|
| Conservative | 1 | 1 | 1.5GB | 1 core |
| Moderate | 2 | 2 | 3GB | 2 cores |
| Aggressive | 3 | 3 | 4.5GB | 3 cores |
| Max | 4+ | 4+ | 6GB+ | 4 cores |

### Time to Register

- **100 accounts**: ~100 minutes (single instance)
- **100 accounts**: ~50 minutes (2 instances)
- **100 accounts**: ~33 minutes (3 instances)

## 🔧 Common Commands

```bash
# Launch 2 instances
./run.sh 2

# Launch 5 instances
./run.sh 5

# Stop all instances
./stop.sh

# View live logs (instance 1)
tail -f logs/register_instance_1.log

# View all logs (follow)
tail -f logs/*.log

# Count registered accounts
wc -l data/registration_success.txt

# Check running instances
ps aux | grep "python3.*register.py"

# Check Docker containers
docker ps | grep gluetun_register

# View container logs
docker logs gluetun_register_1

# Kill specific instance
kill <PID>

# Free up port
sudo lsof -i :8888 | awk 'NR!=1 {print $2}' | xargs kill -9
```

## 🎓 Learning Path

1. **Read**: `QUICKSTART.md` (5 mins) - Get running
2. **Understand**: `register.py` - Main logic
3. **Reference**: `README.md` - Full docs
4. **Advanced**: `DEPLOYMENT.md` - Architecture details

## ✅ What's Included

- ✅ Multi-instance support with unique containers per instance
- ✅ Automatic port allocation (8888, 8988, 9088, ...)
- ✅ Per-instance logging and monitoring
- ✅ Browser fingerprinting (geolocation, timezone, viewport)
- ✅ Proxy rotation via gluetun + NordVPN
- ✅ Automatic account verification
- ✅ CSV export of results
- ✅ Graceful shutdown
- ✅ Full error handling
- ✅ Production-ready

## 🚫 What's NOT Included

- ❌ Account usage/posting logic (beyond creation)
- ❌ Account farming/monetization (out of scope)
- ❌ Advanced proxying (beyond gluetun)
- ❌ Dashboard/UI (CLI-based only)

## 📝 Example Output

After running `./run.sh 3`:

```
[INFO] Instance 1: Creating account #1...
[INFO] Instance 2: Creating account #1...
[INFO] Instance 3: Creating account #1...
[SUCCESS] Instance 1: Registered account sarah_a1b2 (185.123.45.67)
[SUCCESS] Instance 2: Registered account mia_c3d4 (192.168.1.50)
[SUCCESS] Instance 3: Registered account bella_e5f6 (10.0.0.1)
[INFO] Instance 1: Restarting proxy...
[INFO] Instance 2: Restarting proxy...
[INFO] Instance 3: Restarting proxy...
```

Output file (`data/registration_success.txt`):

```csv
sarah_a1b2,sarah_a1b2@gmail.com,13123244,Dublin,185.123.45.67,1
mia_c3d4,mia_c3d4@gmail.com,13123244,London,192.168.1.50,2
bella_e5f6,bella_e5f6@gmail.com,13123244,Berlin,10.0.0.1,3
```

## 🔐 Security Notes

- NordVPN credentials stored in `config.json` (don't commit to git)
- `.gitignore` configured to skip logs, data, config
- Each instance uses unique container to prevent conflicts
- Ports are isolated (8888, 8988, 9088, etc.)

## 📞 Support

- **Setup issues**: Check `QUICKSTART.md`
- **Technical details**: Read `README.md`
- **Architecture questions**: See `DEPLOYMENT.md`
- **Troubleshooting**: `README.md` → Troubleshooting section

## 🎉 Next Steps

1. Copy folder to VPS
2. Edit `config.json` with credentials
3. Run `./run.sh 3` to start 3 instances
4. Monitor with `tail -f logs/register_instance_1.log`
5. Collect results from `data/registration_success.txt`

---

**Ready to deploy!** Start with QUICKSTART.md 🚀
