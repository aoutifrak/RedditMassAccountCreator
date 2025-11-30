#!/bin/bash
#
# Multi-instance launcher for Reddit Account Registration
# Usage: ./run.sh [number_of_instances]
# Example: ./run.sh 3    (launches 3 instances)
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NUM_INSTANCES=${1:-1}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Reddit Account Registration - Multi-Instance Launcher${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Verify config exists
if [ ! -f "$SCRIPT_DIR/config.json" ]; then
    echo -e "${RED}✗ config.json not found!${NC}"
    echo -e "${YELLOW}Please create config.json with NordVPN credentials${NC}"
    exit 1
fi

# Verify Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python3 not found!${NC}"
    exit 1
fi

# Verify Docker is available
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker not found!${NC}"
    echo -e "${YELLOW}Please install Docker${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Dependencies verified${NC}"
echo -e "${GREEN}Starting $NUM_INSTANCES instance(s)...${NC}"
echo ""

# Create logs directory if it doesn't exist
mkdir -p "$SCRIPT_DIR/logs"
mkdir -p "$SCRIPT_DIR/data"

# Launch instances
PIDS=()
for i in $(seq 1 $NUM_INSTANCES); do
    echo -e "${GREEN}[Instance $i]${NC} Starting in background..."
    
    # Run instance in background with nohup to keep running even after terminal closes
    nohup xvfb-run python3 "$SCRIPT_DIR/register.py" --instance $i > "$SCRIPT_DIR/logs/instance_$i.out" 2>&1 &
    PID=$!
    PIDS+=($PID)
    
    echo -e "${GREEN}[Instance $i]${NC} PID: $PID"
    echo -e "${YELLOW}[Instance $i]${NC} Log file: $SCRIPT_DIR/logs/register_instance_$i.log"
    
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
echo -e "${YELLOW}Commands:${NC}"
echo "  View logs:    tail -f logs/register_instance_1.log"
echo "  View output:  cat logs/instance_1.out"
echo "  Kill instance 1: kill ${PIDS[0]}"
echo "  Kill all:     ./stop.sh"
echo ""
echo -e "${GREEN}Press Ctrl+C to continue, instances will keep running in background${NC}"

# Wait for Ctrl+C
trap "echo ''; echo 'Instances continue running in background'" INT
wait
