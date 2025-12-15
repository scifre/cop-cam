# Quick Start Guide

## Test Backend (No Video Files Required)

### Step 1: Start Test Backend

```bash
cd backend
python test_backend.py
```

This will start the test backend on port **8001** and automatically generate simulated detections.

### Step 2: Configure Frontend for Test Backend

```bash
cd frontend
cp .env.test .env
```

Or manually create `.env`:

```env
VITE_BACKEND_URL=http://localhost:8001
VITE_WS_URL=ws://localhost:8001
```

### Step 3: Start Frontend

```bash
cd frontend
npm install  # First time only
npm run dev
```

Open http://localhost:3000 and you'll see simulated detections appearing on the map!

## Real Backend (With Video Files)

### Step 1: Process Videos (Offline)

```bash
# Place videos in cctv/ folder
python offline_preprocess.py
```

### Step 2: Start Real Backend

```bash
cd backend
SIMULATION_MODE=true python main.py
```

### Step 3: Configure Frontend for Real Backend

```bash
cd frontend
cp .env.production .env
```

Or manually:

```env
VITE_BACKEND_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

### Step 4: Start Frontend

```bash
cd frontend
npm run dev
```

## Quick Switch Between Backends

Use the helper script:

```bash
# Switch to test backend
./switch_backend.sh test

# Switch to real backend
./switch_backend.sh real
```

Then restart your frontend dev server.

## Environment Files

- `frontend/.env.test` - Pre-configured for test backend
- `frontend/.env.production` - Pre-configured for real backend
- `frontend/.env.example` - Template (copy to `.env` and customize)

## Ports

- **8000** - Real backend (main.py)
- **8001** - Test backend (test_backend.py)
- **3000** - Frontend (Vite dev server)

## Troubleshooting

**Frontend not connecting:**
- Check that the backend is running
- Verify `.env` file has correct URLs
- Check browser console for errors
- Make sure ports match (8000 for real, 8001 for test)

**No detections appearing:**
- Test backend: Should auto-generate detections
- Real backend: Make sure `SIMULATION_MODE=true` and simulation data exists

**Switching backends:**
- Always restart frontend dev server after changing `.env`
- Or use `./switch_backend.sh` helper script

