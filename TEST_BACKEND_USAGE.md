# Test Backend Usage Guide

## Overview

The test backend (`test_backend.py`) generates simulated detections without requiring video files or GPU processing. This is perfect for testing the frontend when you don't have video files available.

## Quick Start

### 1. Start Test Backend

```bash
cd backend
python test_backend.py
```

The test backend will start on port **8001** by default (configurable via `TEST_BACKEND_PORT` environment variable).

### 2. Configure Frontend

Create a `.env` file in the `frontend/` directory:

```bash
cd frontend
cp .env.example .env
```

Edit `.env` to use the test backend:

```env
VITE_BACKEND_URL=http://localhost:8001
VITE_WS_URL=ws://localhost:8001
```

Or use the pre-configured test environment:

```bash
cp .env.test .env
```

### 3. Start Frontend

```bash
cd frontend
npm install  # if not already done
npm run dev
```

The frontend will connect to the test backend and display simulated detections.

## Test Backend Features

- **Automatic Detection Generation**: Generates detections every 2-8 seconds
- **Realistic Simulation**: Mix of criminals (Category B) and police (Category A)
- **Multiple Cameras**: Randomly selects from 6 cameras
- **WebSocket Support**: Real-time detection broadcasting (same as real backend)
- **Same API**: Compatible with all frontend endpoints

## Test Data

The test backend uses predefined test data:

**Criminals:**
- Rahul Verma (CRIM_001)
- Vikash Singh (CRIM_002)
- Ajay Kumar (CRIM_003)

**Police:**
- Officer Sharma (POLICE_001)
- Officer Patel (POLICE_002)

## API Endpoints

All endpoints match the real backend:

- `GET /get-detections` - Get all detections
- `POST /report-detection` - Report a detection (for compatibility)
- `GET /cameras` - Get camera list
- `GET /simulation/status` - Get simulation status
- `POST /simulation/start` - Start simulation
- `POST /simulation/stop` - Stop simulation
- `GET /test/info` - Get test backend information

## Environment Variables

### Backend (.env)

```env
# Test backend port
TEST_BACKEND_PORT=8001
```

### Frontend (.env)

```env
# Use test backend
VITE_BACKEND_URL=http://localhost:8001
VITE_WS_URL=ws://localhost:8001

# Or use real backend
VITE_BACKEND_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

## Switching Between Test and Real Backend

### Option 1: Use .env file

Edit `frontend/.env`:

```env
# For test backend
VITE_BACKEND_URL=http://localhost:8001
VITE_WS_URL=ws://localhost:8001

# For real backend
VITE_BACKEND_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

Then restart the frontend dev server.

### Option 2: Use different .env files

```bash
# Use test backend
cp frontend/.env.test frontend/.env

# Use real backend
cp frontend/.env.production frontend/.env
```

## Running Both Backends Simultaneously

You can run both backends at the same time:

```bash
# Terminal 1: Real backend (port 8000)
cd backend
python main.py

# Terminal 2: Test backend (port 8001)
cd backend
python test_backend.py

# Terminal 3: Frontend (switch via .env)
cd frontend
npm run dev
```

Just update the frontend `.env` file to switch between them.

## Notes

- Test backend generates detections automatically on startup
- Only Category B (criminal) detections are broadcast via WebSocket
- Detections appear randomly across all 6 cameras
- No video processing or GPU required
- Perfect for frontend development and testing

