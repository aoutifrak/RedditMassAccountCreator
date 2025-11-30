#!/bin/bash
#
# Stop all running instances
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Finding and stopping all register.py instances...${NC}"

# Find all register.py processes and kill them
INSTANCES=$(pgrep -f "python3.*register.py" || true)

if [ -z "$INSTANCES" ]; then
    echo -e "${YELLOW}No running instances found${NC}"
    exit 0
fi

echo -e "${YELLOW}Stopping instances:${NC}"
echo "$INSTANCES" | while read PID; do
    echo "  Killing PID $PID"
    kill -15 $PID 2>/dev/null || true
done

# Wait a moment for graceful shutdown
sleep 2

# Force kill any remaining processes
REMAINING=$(pgrep -f "python3.*register.py" || true)
if [ ! -z "$REMAINING" ]; then
    echo -e "${YELLOW}Force killing remaining instances...${NC}"
    echo "$REMAINING" | while read PID; do
        echo "  Force killing PID $PID"
        kill -9 $PID 2>/dev/null || true
    done
fi

# stop docker containers
echo -e "${YELLOW}Stopping Gluetun Docker containers...${NC}"
DOCKER_CONTAINERS=$(docker ps --filter "name=gluetun-register-" --format "{{.ID}}")
if [ -z "$DOCKER_CONTAINERS" ]; then
    echo -e "${YELLOW}No Gluetun containers found${NC}"
else
    echo "$DOCKER_CONTAINERS" | while read CONTAINER_ID; do
        echo "  Stopping container ID $CONTAINER_ID"
        docker stop $CONTAINER_ID 2>/dev/null || true
    done
fi  

echo -e "${GREEN}✓ All instances stopped${NC}"
