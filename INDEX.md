# 📚 Reddit Account Registration VPS - Package Index

## 🎯 START HERE

**New to this package?** Read in this order:

1. **PACKAGE_INFO.md** ← Overview & architecture (you are here!)
2. **QUICKSTART.md** ← 5-minute setup guide
3. **register.py** ← Main script
4. **README.md** ← Full documentation
5. **DEPLOYMENT.md** ← Advanced reference

---

## 📁 Complete File Reference

### 🚀 Executable Scripts

| File | Purpose | Usage |
|------|---------|-------|
| `register.py` | Main registration script (34 KB) | `python3 register.py --instance 1` |
| `run.sh` | Multi-instance launcher | `./run.sh 3` |
| `stop.sh` | Stop all instances | `./stop.sh` |

### 📋 Documentation

| File | Size | Purpose | Read If |
|------|------|---------|---------|
| **QUICKSTART.md** | 3 KB | 5-min setup | You want to get running NOW |
| **README.md** | 7.4 KB | Complete guide | You need full documentation |
| **DEPLOYMENT.md** | 8.7 KB | Architecture details | You want to understand how it works |
| **PACKAGE_INFO.md** | 7.7 KB | Package overview | You're exploring the system |
| **This file** | - | File index | You're lost |

### ⚙️ Configuration

| File | Purpose | Action |
|------|---------|--------|
| `config.json` | VPN credentials | **MUST EDIT** with NordVPN account |
| `requirements.txt` | Python dependencies | `pip3 install -r requirements.txt` |
| `.gitignore` | Git configuration | Leave as-is (ignore logs, data) |

### 📁 Runtime Folders

| Folder | Purpose | Created By |
|--------|---------|-----------|
| `logs/` | Instance logs | Scripts (at runtime) |
| `data/` | Registered accounts | Scripts (at runtime) |

---

## 🎓 Reading Guide by Use Case

### "I want to get it running right now"
```
→ QUICKSTART.md (5 mins)
  → config.json (edit)
  → ./run.sh 3 (start)
```

### "I want to understand what this does"
```
→ PACKAGE_INFO.md (overview)
  → README.md (features & setup)
  → register.py (implementation)
```

### "I want production deployment details"
```
→ DEPLOYMENT.md (architecture)
  → README.md (troubleshooting)
  → run.sh (multi-instance)
```

### "I'm having a problem"
```
→ README.md → Troubleshooting section
  OR
→ DEPLOYMENT.md → Issue-specific guidance
```

---

## 📊 File Statistics

```
Total Size: ~100 KB (without runtime dependencies)

Scripts:    36 KB
  - register.py: 34 KB (~1100 lines, multi-instance support)
  - run.sh: 2.6 KB (launcher)
  - stop.sh: 1.1 KB (shutdown)

Documentation: 26 KB
  - README.md: 7.4 KB
  - DEPLOYMENT.md: 8.7 KB
  - PACKAGE_INFO.md: 7.7 KB
  - QUICKSTART.md: 3.0 KB

Config: 298 B
  - config.json: 227 B (EDIT THIS)
  - requirements.txt: 71 B
  - .gitignore: 289 B
```

---

## ⚡ Quick Reference Commands

```bash
# Setup
pip3 install -r requirements.txt
nano config.json  # Edit with credentials
chmod +x register.py run.sh stop.sh

# Run
python3 register.py --instance 1    # Single instance
./run.sh 2                          # 2 instances in parallel
./run.sh 5                          # 5 instances in parallel

# Monitor
tail -f logs/register_instance_1.log
ps aux | grep register.py
docker ps | grep gluetun_register

# Stop
./stop.sh
pkill -f "python3.*register.py"

# Results
cat data/registration_success.txt
wc -l data/registration_success.txt
```

---

## 🔑 Key Features at a Glance

```
✅ Multi-instance support        (run 2-5 instances on one VPS)
✅ Auto port allocation          (8888, 8988, 9088, ...)
✅ Unique gluetun containers     (per instance)
✅ Per-instance logging          (logs/register_instance_N.log)
✅ Browser automation            (Zendriver + Chrome)
✅ Proxy management              (gluetun + NordVPN)
✅ Account verification          (Reddit status check)
✅ CSV export                    (data/registration_success.txt)
✅ Production-ready              (error handling, graceful shutdown)
✅ Easy deployment               (~5 minutes setup)
```

---

## 🚀 Deployment Path

```
Step 1: Read QUICKSTART.md                (2 mins)
Step 2: Edit config.json                  (1 min)
Step 3: pip3 install -r requirements.txt  (2 mins)
Step 4: python3 register.py --instance 1  (test)
Step 5: ./run.sh 3                        (production)
Step 6: tail -f logs/register_instance_1.log  (monitor)

Total: ~5-10 minutes to first registration
```

---

## 📞 Common Questions

**Q: Where do I start?**
A: Read QUICKSTART.md (3 mins) then edit config.json

**Q: How do I run multiple instances?**
A: `./run.sh 3` (launches 3 instances in parallel)

**Q: Where are my registered accounts?**
A: `data/registration_success.txt` (CSV format)

**Q: How do I stop everything?**
A: `./stop.sh`

**Q: What's the port number for instance 2?**
A: 8988 (formula: 8888 + (instance-1)*100)

**Q: Can I run this without Docker?**
A: No, gluetun requires Docker for VPN proxy

**Q: Can I use a different VPN?**
A: Yes, edit config.json (supports NordVPN, ExpressVPN, etc.)

**Q: How much RAM per instance?**
A: ~1.5GB (browser + proxy container)

---

## 🎁 What's Inside register.py

The standalone script includes:

```python
# Core Features
✓ CLI argument parsing (--instance N)
✓ Instance-specific logging setup
✓ Docker container management
✓ Gluetun proxy lifecycle
✓ Browser automation (Zendriver)
✓ Reddit account registration
✓ IP geolocation detection
✓ Browser fingerprinting
✓ Cookie handling
✓ Form filling & submission
✓ Account verification
✓ Error handling & recovery
✓ CSV data export

# Multi-Instance Support
✓ Unique container names per instance
✓ Auto port allocation per instance
✓ Per-instance log files
✓ Instance tracking in output
```

---

## 🎯 Next Steps

1. **If new**: Read QUICKSTART.md (next file)
2. **If deploying**: Edit config.json, run setup commands
3. **If scaling**: Use `./run.sh N` for N instances
4. **If monitoring**: Use `tail -f logs/register_instance_*.log`
5. **If having issues**: Check README.md troubleshooting

---

**Ready?** → Open QUICKSTART.md 🚀
