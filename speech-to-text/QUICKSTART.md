# Speech-to-Text Quick Start Guide

Get up and running in 5 minutes!

## Prerequisites

- Python 3.8 or higher
- Microphone (for live recording)
- OpenAI API key

## Setup Steps

### 1. Create Virtual Environment

```bash
cd speech-to-text
python -m venv venv

# Activate (Mac/Linux)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your OpenAI API key
# Open .env in your editor and set:
OPENAI_API_KEY=sk-your-actual-api-key-here
```

### 4. Test Your Setup

```bash
# Run the test suite
python tests/test_transcription.py
```

You should see:
```
TEST RESULTS: 7 passed, 0 failed
```

### 5. Start the Server

```bash
cd src
python main.py
```

You should see:
```
============================================================
Speech-to-Text API Server
============================================================
Port: 8001
...
```

## Quick Test

In another terminal, test the API:

```bash
# Health check
curl http://localhost:8001/health

# Start a session
curl -X POST http://localhost:8001/sessions/start

# You'll get a response like:
# {
#   "session_id": "session-abc123...",
#   "status": "started",
#   ...
# }
```

## Testing with cURL

### Start a session and get the stream:

```bash
# Terminal 1: Start streaming (replace SESSION_ID with actual ID)
curl http://localhost:8001/sessions/SESSION_ID/stream

# This will wait for transcript chunks...
# Speak into your microphone and you'll see chunks appear!
```

### Stop the session:

```bash
# Terminal 2: Stop the session
curl -X POST http://localhost:8001/sessions/SESSION_ID/stop
```

## Testing with a File

If you have an audio file to test:

```bash
curl -X POST http://localhost:8001/transcribe/upload \
  -F "audio=@your-audio-file.wav"
```

## Next Steps

- See [README.md](./README.md) for full API documentation
- Check [../docs/integration.md](../docs/integration.md) for integration details
- Frontend team can now connect to `http://localhost:8001`

## Troubleshooting

### "sounddevice not working"
- **Mac**: Install PortAudio: `brew install portaudio`
- **Linux**: `sudo apt-get install portaudio19-dev python3-pyaudio`
- **Windows**: Should work out of the box

### "No microphone detected"
```bash
# List available devices
python src/audio_capture.py
```

### "OpenAI API errors"
- Check your API key in `.env`
- Verify you have credits: https://platform.openai.com/account/usage
- Check rate limits

### "Empty transcriptions"
- Speak louder or closer to the microphone
- Check audio levels with: `python src/audio_capture.py`

## Architecture Overview

```
audio (microphone)
    ↓
AudioCapture (capture.py)
    ↓
AudioBuffer (buffer.py) ← Smart chunking (8s + 1s overlap)
    ↓
TranscriptionService (transcription_service.py) ← OpenAI GPT-4o Transcribe (with speaker diarization)
    ↓
SessionManager (session_manager.py) ← Track sessions & speaker labels
    ↓
Flask API (main.py) ← SSE streaming
    ↓
Frontend (your React app)
```

## Key Features Implemented

✅ **Speaker diarization** - Automatically identifies who's speaking (A, B, C, etc.)
✅ **8-second chunks** with 1-second overlap
✅ **Silence detection** for adaptive chunking
✅ **Smart deduplication** of overlapping text
✅ **Real-time streaming** via Server-Sent Events
✅ **Session management** with automatic cleanup
✅ **Error handling** with retry logic
✅ **CORS support** for frontend integration

## Configuration

Edit `.env` to customize:

```env
# Change chunk duration (default: 8 seconds)
CHUNK_DURATION_SECONDS=8

# Change overlap (default: 1 second)
OVERLAP_DURATION_SECONDS=1

# Enable silence detection (default: 2 seconds)
SILENCE_THRESHOLD_SECONDS=2.0

# Server port (default: 8001)
PORT=8001
```

## Need Help?

- Check the main [README.md](./README.md)
- See [../docs/architecture.md](../docs/architecture.md)
- Ask the team!

Happy coding! 🎤✨
