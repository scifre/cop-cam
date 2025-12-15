# Cop-Cam Simulation Mode Usage Guide

## Overview

The Cop-Cam system now supports **offline preprocessing** and **real-time simulation** to avoid GPU memory issues when processing multiple CCTV videos.

## Architecture

### Phase 1: Offline Preprocessing (GPU Required)
Processes videos sequentially and saves all detection data to disk.

### Phase 2: Real-Time Simulation (No GPU Required)
Backend replays preprocessed detections in real-time via WebSocket.

## Usage

### Step 1: Place CCTV Videos

Place your CCTV video files (`.mp4`, `.avi`, `.mov`, `.mkv`, `.flv`) in the `cctv/` directory:

```bash
cctv/
  ├── video_1.mp4
  ├── video_2.mp4
  ├── video_3.mp4
  ├── video_4.mp4
  ├── video_5.mp4
  └── video_6.mp4
```

### Step 2: Run Offline Preprocessing

Process all videos sequentially:

```bash
python offline_preprocess.py
```

This will:
- Process videos one by one (no parallel processing)
- Detect and track faces using InsightFace + DeepSORT
- Perform face recognition using LanceDB
- Save all detections to `simulation_data/`

**Output Structure:**
```
simulation_data/
  ├── detections/
  │   ├── CAM_01.json
  │   ├── CAM_02.json
  │   └── ...
  ├── timeline.json          # Global timeline of all detections
  ├── criminals.json         # Criminal metadata
  ├── embeddings/            # Face embeddings per identity
  └── faces/                 # Face images
```

### Step 3: Run Backend in Simulation Mode

Start the backend with `SIMULATION_MODE=true`:

```bash
cd backend
SIMULATION_MODE=true python main.py
```

Or using uvicorn:

```bash
cd backend
SIMULATION_MODE=true uvicorn main:app --host 0.0.0.0 --port 8000
```

The backend will:
- Load simulation data on startup
- Automatically start replaying detections after 3 seconds
- Emit detections via WebSocket (same format as live mode)
- **No GPU required** - all processing was done offline

### Step 4: Start Frontend

The frontend works unchanged:

```bash
cd frontend
npm install
npm run dev
```

The frontend will receive detections via WebSocket and display them on the map in real-time.

## Simulation Control Endpoints

### Start Simulation
```bash
POST /simulation/start?speed=1.0
```

### Stop Simulation
```bash
POST /simulation/stop
```

### Check Status
```bash
GET /simulation/status
```

## Live Mode (Original)

To use the original live processing mode, simply don't set `SIMULATION_MODE`:

```bash
cd backend
python main.py
```

Then run `model_integration.py` to process videos in real-time (requires GPU).

## Notes

- Videos are assigned to cameras sequentially (video 1 → cam_01, video 2 → cam_02, etc.)
- Global timeline ensures all videos are synchronized on a single clock
- Only Category B (criminal) detections are broadcast via WebSocket
- Face recognition uses 10-frame stabilization (majority vote)
- All detections are saved after stabilization

## Troubleshooting

**No simulation data found:**
- Make sure you've run `offline_preprocess.py` first
- Check that `simulation_data/timeline.json` exists

**Simulation not starting:**
- Check backend logs for errors
- Verify WebSocket connections are established
- Use `/simulation/status` endpoint to check status

**Frontend not receiving detections:**
- Ensure backend is running in simulation mode
- Check browser console for WebSocket connection errors
- Verify frontend is connecting to correct backend URL

