#!/bin/bash
#
# Run script for Reddit Account Registration
# Usage: ./run.sh [number_of_instances] [options]
# Example: ./run.sh 3              (launches 3 instances with proxies)
# Example: ./run.sh 1 --no-proxy   (launches 1 instance without proxy)
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NUM_INSTANCES=${1:-1}
shift 2>/dev/null || true  # Remove first argument, ignore error if none

# Collect remaining arguments to pass to python script
EXTRA_ARGS="$@"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Reddit Account Registration - Launcher${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Activate virtual environment if it exists
if [ -d "$SCRIPT_DIR/venv" ]; then
    source "$SCRIPT_DIR/venv/bin/activate"
    echo -e "${GREEN}✓ Virtual environment activated${NC}"
else
    echo -e "${YELLOW}Warning: Virtual environment not found. Run setup.sh first.${NC}"
fi

# Verify Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python3 not found!${NC}"
    echo -e "${YELLOW}Please run setup.sh first${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python3 available${NC}"

# Check if --no-proxy flag is set
NO_PROXY=false
for arg in $EXTRA_ARGS; do
    if [ "$arg" == "--no-proxy" ]; then
        NO_PROXY=true
        break
    fi
done

# Only check proxies if not using --no-proxy
if [ "$NO_PROXY" = false ]; then
    if [ -f "$SCRIPT_DIR/proxy.txt" ]; then
        PROXY_COUNT=$(grep -v '^#' "$SCRIPT_DIR/proxy.txt" 2>/dev/null | grep -v '^$' | wc -l)
        if [ "$PROXY_COUNT" -gt 0 ]; then
            echo -e "${GREEN}✓ Found $PROXY_COUNT proxies in proxy.txt${NC}"
        else
            echo -e "${YELLOW}Warning: No proxies in proxy.txt. Use --no-proxy to run without proxies.${NC}"
        fi
    else
        echo -e "${YELLOW}Warning: proxy.txt not found. Use --no-proxy to run without proxies.${NC}"
    fi
else
    echo -e "${GREEN}✓ Running in no-proxy mode (direct connection)${NC}"
fi

# Check for xvfb-run
XVFB_AVAILABLE=false
if command -v xvfb-run &> /dev/null; then
    XVFB_AVAILABLE=true
    echo -e "${GREEN}✓ xvfb-run available${NC}"
else
    echo -e "${YELLOW}Warning: xvfb-run not found. Browser may need a display.${NC}"
fi

echo ""
echo -e "${GREEN}Starting $NUM_INSTANCES instance(s)...${NC}"
if [ -n "$EXTRA_ARGS" ]; then
    echo -e "${YELLOW}Extra arguments: $EXTRA_ARGS${NC}"
fi
echo ""

# Create logs directory if it doesn't exist
mkdir -p "$SCRIPT_DIR/logs"
mkdir -p "$SCRIPT_DIR/data"

# Launch instances
PIDS=()
for i in $(seq 1 $NUM_INSTANCES); do
    echo -e "${GREEN}[Instance $i]${NC} Starting in background..."
    
    if [ "$XVFB_AVAILABLE" = true ]; then
        # Run with xvfb for headless display
        nohup xvfb-run -a --server-args='-screen 0 1920x1080x24 -ac' \
            python3 "$SCRIPT_DIR/reddit_register.py" --instance $i $EXTRA_ARGS \
            > "$SCRIPT_DIR/logs/instance_$i.out" 2>&1 &
    else
        # Run without xvfb
        python3 "$SCRIPT_DIR/reddit_register.py" --instance $i $EXTRA_ARGS \
            > "$SCRIPT_DIR/logs/instance_$i.out" 2>&1 &
    fi
    
    PID=$!
    PIDS+=($PID)
    
    echo -e "${GREEN}[Instance $i]${NC} PID: $PID"
    echo -e "${YELLOW}[Instance $i]${NC} Log file: $SCRIPT_DIR/logs/instance_$i.log"
    echo -e "${YELLOW}[Instance $i]${NC} Output: $SCRIPT_DIR/logs/instance_$i.out"
    
    # Small delay between starting instances
    sleep 2
done

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}All instances started!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}PIDs:${NC}"
for i in "${!PIDS[@]}"; do
    instance=$((i+1))
    echo "  Instance $instance: ${PIDS[$i]}"
done
echo ""
echo -e "${YELLOW}Useful commands:${NC}"
echo "  View logs:      tail -f logs/instance_1.log"
echo "  View output:    tail -f logs/instance_1.out"
echo "  View accounts:  cat data/accounts.txt"
echo "  Count accounts: wc -l data/accounts.txt"
echo "  Kill instance:  kill ${PIDS[0]}"
echo "  Kill all:       pkill -f reddit_register.py"
echo ""
echo -e "${YELLOW}Usage examples:${NC}"
echo "  ./run.sh 1 --no-proxy                              # Run without proxy"
echo "  ./run.sh 2 --ssh-host server.com --ssh-user user   # With SSH upload"
echo ""
echo -e "${GREEN}Instances running in background. Press Ctrl+C to exit this script.${NC}"
