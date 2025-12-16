# CCTV Face Recognition System

Complete offline CCTV video processing and visualization system with face recognition.

## System Overview

This project consists of three main components:

1. **Offline Video Processor** - Processes CCTV videos with face recognition
2. **Frontend Dashboard** - React-based visualization of processed videos
3. **Face Database** - LanceDB-based storage for face embeddings

## Quick Start

### 1. Setup Environment

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies (if not already done)
pip install -r requirements.txt
```

### 2. Populate Face Database

```bash
# Add faces from new_photos/ directory
python add_faces_from_new_photos.py
```

### 3. Process Videos

```bash
# Process all CCTV videos
python offline_processor/process_videos.py
```

This will:
- Process all videos in `cctv_videos/`
- Create annotated videos in `processed_data/videos/`
- Generate `processed_data/detections.json` with detection timeline

### 4. Setup Frontend Data

```bash
# Copy processed data to frontend
python setup_frontend_data.py
```

### 5. Run Frontend

```bash
cd frontend
npm install  # First time only
npm run dev
```

Open http://localhost:5173 in your browser.

## Project Structure

```
cop-cam/
├── cctv_videos/              # Input CCTV videos
├── new_photos/               # Face images to add to database
├── face_db/                  # LanceDB face database
├── processed_data/           # Output from offline processor
│   ├── videos/               # Annotated videos (CAM_XX.mp4)
│   └── detections.json       # Detection timeline
├── offline_processor/        # Video processing scripts
│   └── process_videos.py     # Main processing script
├── frontend/                 # React frontend
│   ├── src/                  # React source code
│   └── public/               # Static files (videos, JSON)
├── helper.py                 # Database utilities
├── test.py                   # Single video test script
└── add_faces_from_new_photos.py  # Face database population
```

## Components

### Offline Processor

Processes multiple CCTV videos sequentially:
- Detects persons using YOLO
- Tracks persons using DeepSort
- Recognizes faces using InsightFace
- Generates annotated videos and detection timeline

**Usage:**
```bash
python offline_processor/process_videos.py
```

### Frontend Dashboard

React-based visualization:
- Multi-camera video grid
- Real-time detection simulation
- Alert system for detected persons
- Recent detections sidebar

**Usage:**
```bash
cd frontend
npm install
npm run dev
```

## Verification

Check that everything is set up correctly:

```bash
python verify_integration.py
```

## Documentation

- [Integration Guide](INTEGRATION_GUIDE.md) - Detailed integration steps
- [Frontend README](frontend/README.md) - Frontend-specific documentation

## Requirements

- Python 3.8+
- Node.js 16+
- CUDA-capable GPU (optional, for faster processing)
- ~10GB disk space for videos and models

## Troubleshooting

### Videos not processing
- Check `cctv_videos/` contains video files
- Verify video formats are supported (MP4 recommended)
- Check GPU availability: `python -c "import torch; print(torch.cuda.is_available())"`

### Frontend not loading
- Run `python setup_frontend_data.py` to copy data
- Check browser console for errors
- Verify `frontend/public/videos/` contains video files

### No detections
- Ensure face database is populated: `python add_faces_from_new_photos.py`
- Check detection threshold in `offline_processor/process_videos.py` (default: 0.80)
- Verify faces are visible in videos

## License

See individual component licenses.

