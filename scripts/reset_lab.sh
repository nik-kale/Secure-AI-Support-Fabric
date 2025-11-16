#!/bin/bash

# Reset Lab Script
# This script resets the lab environment by stopping containers and clearing data

set -e

echo "================================================"
echo "AI Support Fabric - Reset Lab Script"
echo "================================================"
echo ""
echo "This will:"
echo "  - Stop all running containers"
echo "  - Remove containers and networks"
echo "  - Clear telemetry data volume"
echo ""

read -p "Are you sure you want to reset the lab? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Reset cancelled."
    exit 0
fi

echo ""
echo "Stopping containers..."
docker-compose down -v

echo ""
echo "✓ Lab reset complete!"
echo ""
echo "To start the lab again:"
echo "  docker-compose up --build"
echo ""
