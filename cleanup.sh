#!/bin/bash
# Cleanup script for Reddit Register VPS
# Frees disk space and cleans up temporary files

echo "🧹 Cleaning up disk space..."

# Stop all instances first
echo "Stopping all instances..."
pkill -f reddit_register.py || true
sleep 2

# Clear /tmp
echo "Clearing /tmp..."
sudo rm -rf /tmp/*
sudo rm -rf /tmp/.X*
sudo rm -rf /tmp/.mozilla*
sudo rm -rf /tmp/camoufox*

# Clear Python cache
echo "Clearing Python cache..."
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Clear old logs (keep last 5MB)
echo "Archiving old logs..."
if [ -d "logs" ]; then
    cd logs
    # Keep only last 10 log files
    ls -1tr *.log 2>/dev/null | head -n -10 | xargs rm -f 2>/dev/null || true
    cd ..
fi

# Clear Firefox cache if exists
echo "Clearing Firefox cache..."
rm -rf ~/.cache/camoufox* 2>/dev/null || true
rm -rf ~/.cache/mozilla* 2>/dev/null || true

# Restart systemd tmpfiles service
echo "Restarting tmpfiles service..."
sudo systemctl restart systemd-tmpfiles-setup.service 2>/dev/null || true

# Show disk usage
echo ""
echo "📊 Disk usage after cleanup:"
df -h /

echo ""
echo "✓ Cleanup complete!"
