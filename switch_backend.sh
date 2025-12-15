#!/bin/bash
# Helper script to switch frontend between test and real backend

FRONTEND_DIR="frontend"
TEST_ENV="$FRONTEND_DIR/.env.test"
PROD_ENV="$FRONTEND_DIR/.env.production"
CURRENT_ENV="$FRONTEND_DIR/.env"

if [ "$1" == "test" ]; then
    echo "Switching to TEST backend..."
    cp "$TEST_ENV" "$CURRENT_ENV"
    echo "✓ Frontend configured to use test backend (port 8001)"
    echo "  Restart your frontend dev server for changes to take effect."
elif [ "$1" == "real" ] || [ "$1" == "production" ]; then
    echo "Switching to REAL backend..."
    cp "$PROD_ENV" "$CURRENT_ENV"
    echo "✓ Frontend configured to use real backend (port 8000)"
    echo "  Restart your frontend dev server for changes to take effect."
else
    echo "Usage: ./switch_backend.sh [test|real]"
    echo ""
    echo "  test   - Switch to test backend (port 8001)"
    echo "  real    - Switch to real backend (port 8000)"
    echo ""
    echo "Current configuration:"
    if [ -f "$CURRENT_ENV" ]; then
        grep "VITE_BACKEND_URL" "$CURRENT_ENV" || echo "  No VITE_BACKEND_URL found"
    else
        echo "  No .env file found"
    fi
fi

