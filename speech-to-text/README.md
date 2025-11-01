# Speech-to-Text Component

Captures audio input and converts it to text transcripts in real-time.

## 📚 Documentation

- **[QUICKSTART.md](./QUICKSTART.md)** - Get running in 5 minutes
- **[INTEGRATION.md](./INTEGRATION.md)** - Complete API reference & integration guide ⭐
- **[README.md](./README.md)** - This file (component overview)
- **[../docs/architecture.md](../docs/architecture.md)** - System architecture
- **[../docs/graph-schema.md](../docs/graph-schema.md)** - Graph data format

## Responsibility

- Capture audio from microphone or file
- Convert speech to text using STT API
- Emit transcript chunks every 5-10 seconds
- Maintain session continuity

## Output Format

This component outputs JSON transcript chunks:

```json
{
  "timestamp": "2025-11-01T10:30:45Z",
  "text": "So I think we should focus on the user experience",
  "session_id": "session-123",
  "chunk_id": 42
}
```

See `../shared/schemas/transcript.json` for the complete schema.

## Setup

### Prerequisites

- Python 3.8+
- Microphone access (for live recording)

### Installation

```bash
cd speech-to-text
pip install -r requirements.txt
```

### Configuration

Create a `.env` file:

```env
# Choose your STT provider

# Option 1: OpenAI Whisper
OPENAI_API_KEY=your-api-key
STT_PROVIDER=openai
STT_MODEL=whisper-1

# Option 2: Deepgram
# DEEPGRAM_API_KEY=your-api-key
# STT_PROVIDER=deepgram

# Option 3: Local Whisper
# STT_PROVIDER=local

# Server config
PORT=8001
CHUNK_DURATION=5  # seconds between transcript chunks
```

## Development

### Project Structure

```
speech-to-text/
├── README.md
├── requirements.txt
├── .env
└── src/
    ├── main.py              # API server
    ├── audio_capture.py     # Audio input handling
    ├── transcription.py     # STT logic
    └── test_stt.py          # Testing script
```

### Running the Service

```bash
python src/main.py
```

This starts an API server on `http://localhost:8001`

### API Endpoints

#### Start Transcription Session

```
POST /transcribe/start
Content-Type: application/json

{
  "session_id": "session-123"
}
```

Returns: `200 OK`

#### Get Transcript Stream (Server-Sent Events)

```
GET /transcribe/stream?session_id=session-123
```

Returns: Stream of transcript chunks

#### Stop Transcription

```
POST /transcribe/stop
Content-Type: application/json

{
  "session_id": "session-123"
}
```

### Testing

Test with a sample audio file:

```bash
python src/test_stt.py --audio sample.mp3
```

Output should be saved to `../shared/examples/test-transcript.json`

## Implementation Guide

### Step 1: Audio Capture

Choose one approach:

**Option A: Live Microphone**
```python
import sounddevice as sd
import numpy as np

def capture_audio(duration=5):
    # Capture 5 seconds of audio
    sample_rate = 16000
    audio = sd.rec(int(duration * sample_rate),
                   samplerate=sample_rate,
                   channels=1)
    sd.wait()
    return audio
```

**Option B: File Upload**
```python
def process_audio_file(filepath):
    # Process pre-recorded audio
    pass
```

### Step 2: Transcription

**Using OpenAI Whisper API**:
```python
import openai

def transcribe_chunk(audio_data):
    response = openai.Audio.transcribe(
        model="whisper-1",
        file=audio_data
    )
    return response['text']
```

**Using Local Whisper**:
```python
import whisper

model = whisper.load_model("base")

def transcribe_chunk(audio_data):
    result = model.transcribe(audio_data)
    return result['text']
```

### Step 3: Chunking Strategy

Emit chunks every 5-10 seconds:

```python
import time
from datetime import datetime

def streaming_transcription(session_id):
    chunk_id = 0
    while session_active:
        # Capture audio chunk
        audio = capture_audio(duration=5)

        # Transcribe
        text = transcribe_chunk(audio)

        # Emit chunk
        chunk = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "text": text,
            "session_id": session_id,
            "chunk_id": chunk_id
        }

        yield chunk
        chunk_id += 1
        time.sleep(5)
```

### Step 4: API Server

Simple Flask example:

```python
from flask import Flask, request, Response
import json

app = Flask(__name__)

@app.route('/transcribe/stream')
def stream():
    session_id = request.args.get('session_id')

    def generate():
        for chunk in streaming_transcription(session_id):
            yield f"data: {json.dumps(chunk)}\n\n"

    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(port=8001)
```

## Integration with Other Components

### Output to Graph Generation

The graph generation component will consume your transcript chunks. Make sure:

1. JSON format matches the schema in `../shared/schemas/transcript.json`
2. Chunks are emitted regularly (5-10 seconds)
3. Session ID is consistent throughout a session
4. Timestamps are in ISO-8601 format

### Testing with Frontend

The frontend will connect to your `/transcribe/stream` endpoint. Test with:

```bash
curl http://localhost:8001/transcribe/stream?session_id=test-123
```

## Common Issues

**Issue**: Audio quality is poor
- **Solution**: Increase sample rate to 16kHz or higher
- **Solution**: Use noise cancellation preprocessing

**Issue**: Transcription is slow
- **Solution**: Use faster model (OpenAI Whisper instead of local)
- **Solution**: Reduce chunk size

**Issue**: Chunks are too short/long
- **Solution**: Adjust `CHUNK_DURATION` in `.env`
- **Solution**: Use voice activity detection to chunk on pauses

**Issue**: Missing words
- **Solution**: Increase chunk overlap
- **Solution**: Use better STT model

## STT Provider Comparison

| Provider | Speed | Cost | Quality | Setup |
|----------|-------|------|---------|-------|
| OpenAI Whisper API | Fast | $0.006/min | Excellent | Easy |
| Deepgram | Fastest | $0.0125/min | Excellent | Easy |
| Local Whisper | Slow | Free | Good | Medium |
| Google Speech-to-Text | Fast | $0.016/min | Excellent | Medium |

**Recommendation for Hackathon**: OpenAI Whisper API (fast, cheap, reliable)

## Next Steps

1. Choose STT provider and set up API keys
2. Implement basic audio capture
3. Test transcription with sample audio
4. Build API server with streaming endpoint
5. Test integration with frontend using mock data
6. Optimize chunk size and timing

## Resources

- [OpenAI Whisper API Docs](https://platform.openai.com/docs/guides/speech-to-text)
- [Deepgram Docs](https://developers.deepgram.com/)
- [SoundDevice Python Library](https://python-sounddevice.readthedocs.io/)
- [Flask Server-Sent Events](https://flask.palletsprojects.com/en/2.3.x/patterns/streaming/)

## Support

Questions? Check:
- `../docs/integration.md` for how this connects to other components
- `../shared/examples/` for sample output format
- `../CLAUDE.md` for project context
