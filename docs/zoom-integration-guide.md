# Zoom Integration Guide

> **Last Updated**: November 2025
> **AI-Assisted Development**: Time estimates reflect use of AI coding assistants

---

## Table of Contents
- [Current Architecture Analysis](#current-architecture-analysis)
- [Integration Options Overview](#integration-options-overview)
- [Detailed Integration Approaches](#detailed-integration-approaches)
- [Technical Requirements](#technical-requirements)
- [Code Changes Required](#code-changes-required)
- [Recommendations](#recommendations)
- [Effort Estimates](#effort-estimates)

---

## Current Architecture Analysis

### What We Have Built

#### 1. Speech-to-Text Service (Production-Ready ✅)
**Location**: `speech-to-text/src/`
**Tech Stack**: Python + Flask + OpenAI Whisper API
**Status**: Fully functional, production-ready

**Key Components:**
- **AudioCapture** (`audio_capture.py`): Captures from local microphone using `sounddevice`
  - 16kHz mono audio
  - Real-time streaming
  - Thread-safe queue
  - Device enumeration support

- **AudioBuffer** (`audio_buffer.py`): Smart audio chunking
  - 8-second chunks with 1-second overlap
  - Silence detection (2s threshold)
  - Automatic deduplication
  - WAV format conversion

- **TranscriptionService** (`transcription_service.py`): OpenAI Whisper integration
  - Retry logic (3 attempts with exponential backoff)
  - Rate limit handling
  - Statistics tracking
  - 95%+ success rate

- **SessionManager** (`session_manager.py`): Session lifecycle management
  - UUID-based session tracking
  - Concurrent session support (max 10)
  - Automatic cleanup (1-hour timeout)
  - Full transcript accumulation

**API Endpoints:**
```
GET    /health                    - Health check
POST   /sessions/start            - Start recording
GET    /sessions/{id}/stream      - Stream transcripts (SSE)
POST   /sessions/{id}/stop        - Stop recording
GET    /sessions/{id}             - Get session info
GET    /sessions                  - List sessions
POST   /transcribe/upload         - Upload audio file
GET    /stats                     - Service statistics
```

#### 2. Graph Generation (Partial Implementation 🚧)
**Location**: `graph-generation/feature_extractor.py`
**Tech Stack**: Python + Anthropic Claude API
**Status**: Feature extraction working

**Capabilities:**
- Extracts entities, concepts, questions, actions, decisions
- LLM-powered semantic analysis
- Structured JSON output

#### 3. Frontend (Documented, Not Built 📋)
**Location**: `frontend/`
**Planned**: Next.js + React + React Flow/D3.js

### Current Data Flow

```
Local Microphone
       ↓
AudioCapture (sounddevice)
       ↓
AudioBuffer (8s chunks, 1s overlap)
       ↓
TranscriptionService (OpenAI Whisper)
       ↓
TranscriptChunk (SSE stream)
       ↓
Graph Generation (LLM)
       ↓
Frontend Visualization
```

### Critical Limitation for Zoom Integration

**Current audio input**: Local microphone only (`sounddevice` library)
**Zoom audio**: Runs in separate process, not accessible by default

**The Integration Challenge**: Getting Zoom meeting audio into our existing pipeline

---

## Integration Options Overview

| Option | Difficulty | Cost | User Setup | Bot Visible | Audio Quality |
|--------|-----------|------|------------|-------------|---------------|
| **1. Desktop Audio Capture** | ⭐ Easy | $0 | High | No | Good |
| **2. Recall.ai Bot Service** | ⭐⭐ Medium | $0.70/hr | None | Yes | Excellent |
| **3. Zoom Apps SDK** | ⭐⭐⭐ Hard | $0 | Low | No | Good* |
| **4. Zoom Meeting SDK Bot** | ⭐⭐⭐⭐ Very Hard | Server costs | None | Yes | Excellent |

**Quality Note**: * Zoom Apps require workarounds for audio access

---

## Detailed Integration Approaches

### Option 1: Desktop Audio Capture ⭐ (Quickest Path)

#### How It Works
```
Zoom Meeting
    ↓
System Audio Output
    ↓
Virtual Audio Cable (Blackhole/VB-Cable)
    ↓
Your Existing AudioCapture
    ↓
Rest of pipeline unchanged!
```

#### What's Required

**User Setup:**
1. Install virtual audio cable:
   - **macOS**: Blackhole (free)
   - **Windows**: VB-Cable (free)
   - **Linux**: PulseAudio loopback
2. Configure audio routing (one-time setup)
3. Select virtual device in your app

**Code Changes (Minimal):**

**1. Update `audio_capture.py`** - Add device selection:
```python
class AudioCapture:
    def __init__(self, ..., device_index=None):  # NEW parameter
        self.device_index = device_index

    def start(self):
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            device=self.device_index,  # Specify device
            # ... rest unchanged
        )
```

**2. Update `main.py`** - Add device selection endpoint:
```python
@app.route('/audio/devices', methods=['GET'])
def list_audio_devices():
    """List available audio input devices."""
    devices = sd.query_devices()
    input_devices = [
        {
            'index': i,
            'name': device['name'],
            'channels': device['max_input_channels']
        }
        for i, device in enumerate(devices)
        if device['max_input_channels'] > 0
    ]
    return jsonify({'devices': input_devices})

@app.route('/sessions/start', methods=['POST'])
def start_session():
    data = request.get_json() or {}
    audio_device = data.get('audio_device')  # NEW: device index

    audio_capture = AudioCapture(
        sample_rate=AudioConfig.SAMPLE_RATE,
        channels=AudioConfig.CHANNELS,
        device_index=audio_device,  # Pass to AudioCapture
        callback=lambda audio: audio_buffer.add_audio(audio)
    )
    # ... rest unchanged
```

**3. Frontend** - Add device selector:
```typescript
// List available devices
const devices = await fetch('/audio/devices').then(r => r.json())

// User selects device
<select onChange={(e) => setAudioDevice(e.target.value)}>
  {devices.map(d => <option value={d.index}>{d.name}</option>)}
</select>

// Start session with selected device
fetch('/sessions/start', {
  method: 'POST',
  body: JSON.stringify({ audio_device: selectedDevice })
})
```

#### Pros & Cons

✅ **Pros:**
- Minimal code changes (< 50 lines)
- Works with existing pipeline (95% reuse)
- No external dependencies
- No API costs
- Full control over data
- Works with Zoom, Meet, Teams, any audio source

❌ **Cons:**
- User must install virtual audio cable
- Setup instructions needed
- Only captures host's audio (not per-speaker)
- Can't scale to multiple meetings simultaneously
- Not suitable for SaaS deployment

#### Best For
- Personal use / internal tools
- Quick MVP validation
- Testing the full pipeline
- Hackathons

---

### Option 2: Recall.ai Bot Service ⭐⭐ (Recommended for Production)

#### How It Works
```
Zoom Meeting URL
    ↓
Recall.ai API (creates bot)
    ↓
Bot joins meeting
    ↓
Audio streams to webhook
    ↓
Your backend receives audio
    ↓
Existing transcription pipeline
```

#### What's Required

**Sign Up:**
1. Create account at recall.ai
2. Get API key
3. Configure webhook endpoint

**Code Changes:**

**1. New file: `zoom-integration/recall_client.py`**
```python
import requests
import os

RECALL_API_URL = "https://api.recall.ai/api/v1"
RECALL_API_KEY = os.getenv("RECALL_API_KEY")

def create_bot(meeting_url, session_id):
    """Create a bot for a Zoom meeting."""
    response = requests.post(
        f"{RECALL_API_URL}/bot",
        headers={"Authorization": f"Bearer {RECALL_API_KEY}"},
        json={
            "meeting_url": meeting_url,
            "bot_name": "Brainstorm Bot",
            "transcription": {
                "provider": "none"  # We use our own Whisper
            },
            "real_time": {
                "webhooks": {
                    "audio_stream": f"https://your-server.com/recall/audio/{session_id}"
                }
            }
        }
    )
    return response.json()

def stop_bot(bot_id):
    """Stop a running bot."""
    requests.delete(
        f"{RECALL_API_URL}/bot/{bot_id}",
        headers={"Authorization": f"Bearer {RECALL_API_KEY}"}
    )
```

**2. New file: `zoom-integration/recall_webhook.py`**
```python
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

@app.route('/recall/audio/<session_id>', methods=['POST'])
def handle_audio_stream(session_id):
    """Receive audio chunks from Recall.ai bot."""
    data = request.json

    # Recall.ai sends audio as URL or base64
    audio_url = data.get('audio_url')

    # Download audio
    audio_response = requests.get(audio_url)
    audio_bytes = audio_response.content

    # Send to existing transcription service
    requests.post(
        f'http://localhost:8005/transcribe/stream/{session_id}',
        data=audio_bytes,
        headers={'Content-Type': 'audio/wav'}
    )

    return jsonify({'status': 'ok'})

@app.route('/recall/start', methods=['POST'])
def start_bot():
    """Start a bot for a meeting."""
    meeting_url = request.json['meeting_url']

    # Create session in your system
    session_response = requests.post('http://localhost:8005/sessions/start')
    session_id = session_response.json()['session_id']

    # Create Recall.ai bot
    from recall_client import create_bot
    bot_data = create_bot(meeting_url, session_id)

    return jsonify({
        'session_id': session_id,
        'bot_id': bot_data['id'],
        'status': 'started'
    })
```

**3. Update `main.py`** - Add streaming endpoint:
```python
@app.route('/transcribe/stream/<session_id>', methods=['POST'])
def transcribe_stream(session_id):
    """Accept streaming audio from external sources."""
    audio_data = request.get_data()

    # Transcribe
    text = transcription_service.transcribe_audio(audio_data)

    # Add to session
    if text and text.strip():
        session_manager.add_transcript_chunk(session_id, text)

    return jsonify({'status': 'ok'})
```

**4. Update `session_manager.py`** - Add meeting metadata:
```python
@dataclass
class Session:
    session_id: str
    started_at: str
    status: str = "active"
    full_transcript: str = ""
    chunks: List[TranscriptChunk] = field(default_factory=list)

    # NEW: Zoom integration fields
    meeting_id: Optional[str] = None
    meeting_platform: Optional[str] = None  # "zoom", "meet", "teams"
    bot_id: Optional[str] = None
    meeting_url: Optional[str] = None
```

**5. Environment variables:**
```env
# .env
RECALL_API_KEY=your-recall-api-key
RECALL_WEBHOOK_URL=https://your-server.com/recall
```

#### Pricing Breakdown

**Recall.ai Costs:**
- Bot recording: **$0.70 per hour**
- Their transcription: $0.15/hr (optional - we use Whisper)
- Storage (after 7 days): $0.05/hr for 30 days

**Your Costs:**
- OpenAI Whisper: ~$0.54 per 30 minutes (existing cost)

**Total: ~$1.24/hour** for Zoom integration + transcription

**For a 1-hour brainstorming session:** $1.24
**For 100 hours/month:** $124/month

#### Pros & Cons

✅ **Pros:**
- No user setup required
- Works with Zoom, Meet, Teams, Webex
- Per-speaker audio streams (perfect diarization)
- Production-ready infrastructure
- Reliable, maintained by Recall.ai
- Can scale to many concurrent meetings
- Clean API integration

❌ **Cons:**
- Ongoing API costs (~$0.70-1.24/hr)
- External dependency
- Bot visible in meeting
- Requires public webhook endpoint
- Need to handle Recall.ai API changes

#### Best For
- Production SaaS deployment
- Multi-user platform
- Professional/enterprise use
- When budget allows for API costs
- Need per-speaker separation

---

### Option 3: Zoom Apps SDK ⭐⭐⭐ (Best UX, Complex)

#### How It Works
```
Zoom Client
    ↓
Zoom App Panel (your UI runs inside Zoom)
    ↓
Zoom Apps SDK (limited capabilities)
    ↓
[WORKAROUND NEEDED FOR AUDIO]
    ↓
Your backend
```

#### What Zoom Apps SDK Provides

**Available APIs:**
```javascript
import zoomSdk from "@zoom/appssdk"

// Meeting context
const context = await zoomSdk.getMeetingContext()
// Returns: { meetingID, participantUUID, timestamp, etc. }

// Participant list
const participants = await zoomSdk.getParticipants()

// Send invitations
await zoomSdk.sendAppInvitation()

// UI controls
await zoomSdk.showNotification()
await zoomSdk.openUrl()
```

**⚠️ NOT Available:**
- ❌ Direct audio stream access
- ❌ Video stream access
- ❌ Real-time transcription access
- ❌ Recording API

#### Audio Access Workaround

Since Zoom Apps SDK doesn't expose audio, you need a hybrid approach:

**Option A: Desktop Audio Capture (Same as Option 1)**
- User runs Zoom App for UI/controls
- Separate desktop app captures system audio
- Zoom App coordinates the session

**Option B: Companion Bot**
- Zoom App provides UI
- Backend deploys Recall.ai bot separately
- Zoom App shows bot status and controls

#### What You'd Build

**1. Zoom App Frontend** (`zoom-app/`)
```javascript
import zoomSdk from "@zoom/appssdk"

const BrainstormApp = () => {
  const [session, setSession] = useState(null)
  const [graph, setGraph] = useState(null)

  const startBrainstorming = async () => {
    // Get meeting context from Zoom
    const context = await zoomSdk.getMeetingContext()

    // Start backend session with meeting info
    const response = await fetch('https://api.yourapp.com/sessions/start', {
      method: 'POST',
      body: JSON.stringify({
        meeting_id: context.meetingID,
        platform: 'zoom'
      })
    })

    const data = await response.json()
    setSession(data)

    // Connect to SSE stream for live updates
    const eventSource = new EventSource(
      `https://api.yourapp.com/sessions/${data.session_id}/stream`
    )

    eventSource.onmessage = (event) => {
      const update = JSON.parse(event.data)
      // Update graph visualization
      setGraph(update.graph)
    }
  }

  return (
    <div className="zoom-app-container">
      <h2>Brainstorm Graph</h2>

      {!session ? (
        <button onClick={startBrainstorming}>
          Start Brainstorming
        </button>
      ) : (
        <>
          <GraphVisualization graph={graph} />
          <TranscriptPanel session={session} />
        </>
      )}

      <p className="help-text">
        Note: Audio capture requires desktop app or bot
      </p>
    </div>
  )
}
```

**2. Zoom App Configuration** (`zoom-app/config.json`)
```json
{
  "name": "Brainstorm Graph",
  "description": "Real-time knowledge graph from meetings",
  "client_id": "your-zoom-client-id",
  "redirect_uri": "https://yourapp.com/auth/callback",
  "scopes": [
    "meeting:read",
    "participant:read"
  ],
  "capabilities": [
    "inMeeting"
  ],
  "home_url": "https://yourapp.com/zoom-app",
  "about_url": "https://yourapp.com/about"
}
```

**3. OAuth Flow** (Required for Zoom Apps)
```javascript
// Backend: OAuth callback handler
app.get('/auth/zoom/callback', async (req, res) => {
  const { code } = req.query

  // Exchange code for access token
  const tokenResponse = await fetch('https://zoom.us/oauth/token', {
    method: 'POST',
    headers: {
      'Authorization': `Basic ${base64(CLIENT_ID:CLIENT_SECRET)}`
    },
    body: new URLSearchParams({
      grant_type: 'authorization_code',
      code,
      redirect_uri: REDIRECT_URI
    })
  })

  const { access_token } = await tokenResponse.json()

  // Store token for user
  // ... token storage logic

  res.redirect('/dashboard')
})
```

#### Deployment Process

1. **Develop Locally**
   - Use Zoom Apps SDK development tools
   - Test with ngrok/localtunnel for webhooks

2. **Submit to Marketplace**
   - Fill out app details
   - Provide screenshots, videos
   - Privacy policy, terms of service
   - Security review

3. **Review Process** (2-4 weeks)
   - Zoom reviews functionality
   - Security audit
   - Compliance check

4. **Approval & Publishing**
   - App available in Zoom Marketplace
   - Users can install directly

#### Pros & Cons

✅ **Pros:**
- Best user experience (native Zoom integration)
- No separate app to download
- Professional appearance
- Can publish to Zoom Marketplace
- One-click install for users
- OAuth handles authentication

❌ **Cons:**
- Still needs audio workaround (desktop capture or bot)
- Complex OAuth implementation
- Marketplace approval required (2-4 weeks)
- Must maintain Zoom App separately
- Learning curve for Zoom Apps SDK
- Limited to Zoom only

#### Best For
- Professional product targeting Zoom users
- When UX is critical
- Long-term product strategy
- Already committed to Zoom ecosystem

---

### Option 4: Zoom Meeting SDK Bot ⭐⭐⭐⭐ (Most Powerful, Most Complex)

#### How It Works
```
Zoom Meeting
    ↓
Your Bot (uses Zoom Meeting SDK)
    ↓
Raw Audio PCM Streams (per speaker)
    ↓
Audio Processing Bridge
    ↓
Your Transcription Pipeline
```

#### What You Get

**Direct Raw Audio Access:**
- PCM 16LE format (perfect for Whisper)
- Per-participant audio streams
- Video streams (if needed)
- Full meeting control

**Platforms Supported:**
- Windows 7+
- macOS 10.13+
- Linux
- ❌ NOT available in Web SDK

#### Architecture

**New Component: Zoom Bot Service**
```
zoom-bot/
├── bot.py              # Main bot application
├── sdk_wrapper.py      # Zoom SDK interface
├── audio_bridge.py     # Audio format conversion
├── meeting_manager.py  # Bot lifecycle
└── requirements.txt
```

#### What You'd Build

**1. Zoom SDK Wrapper** (`zoom-bot/sdk_wrapper.py`)
```python
from zoom_sdk import ZoomSDK  # Hypothetical SDK binding

class ZoomMeetingBot:
    def __init__(self, api_key, api_secret):
        self.sdk = ZoomSDK()
        self.api_key = api_key
        self.api_secret = api_secret

    def join_meeting(self, meeting_id, password, session_id):
        """Join a Zoom meeting as a bot."""

        # Generate SDK JWT
        jwt_token = self.generate_jwt(meeting_id)

        # Configure SDK
        self.sdk.initialize(self.api_key, self.api_secret)
        self.sdk.enable_raw_audio_data(True)  # Enable raw audio

        # Join meeting
        join_params = {
            'meeting_number': meeting_id,
            'password': password,
            'display_name': 'Brainstorm Bot',
            'token': jwt_token
        }

        self.sdk.join_meeting(join_params)

        # Register audio callback
        self.sdk.on_audio_raw_data_received(
            lambda audio: self.handle_audio(audio, session_id)
        )

    def handle_audio(self, audio_data, session_id):
        """Process raw audio from Zoom."""
        # audio_data contains:
        # - PCM 16LE raw bytes
        # - Sample rate (typically 32kHz)
        # - Participant ID (for per-speaker)

        # Convert to WAV
        wav_bytes = self.pcm_to_wav(
            audio_data.buffer,
            sample_rate=audio_data.sample_rate
        )

        # Send to transcription service
        self.send_to_transcription(wav_bytes, session_id)

    def pcm_to_wav(self, pcm_data, sample_rate):
        """Convert PCM to WAV format."""
        import wave
        import io

        wav_io = io.BytesIO()
        with wave.open(wav_io, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm_data)

        return wav_io.getvalue()

    def send_to_transcription(self, audio_bytes, session_id):
        """Send audio to existing transcription service."""
        requests.post(
            f'http://localhost:8005/transcribe/stream/{session_id}',
            data=audio_bytes,
            headers={'Content-Type': 'audio/wav'}
        )
```

**2. Bot Manager** (`zoom-bot/meeting_manager.py`)
```python
from flask import Flask, request, jsonify
from sdk_wrapper import ZoomMeetingBot

app = Flask(__name__)
active_bots = {}  # bot_id -> ZoomMeetingBot instance

@app.route('/bot/join', methods=['POST'])
def join_meeting():
    """Create bot and join Zoom meeting."""
    data = request.json

    meeting_id = data['meeting_id']
    password = data.get('password', '')
    session_id = data['session_id']

    # Create bot instance
    bot = ZoomMeetingBot(
        api_key=os.getenv('ZOOM_SDK_KEY'),
        api_secret=os.getenv('ZOOM_SDK_SECRET')
    )

    # Join meeting
    bot.join_meeting(meeting_id, password, session_id)

    bot_id = str(uuid.uuid4())
    active_bots[bot_id] = bot

    return jsonify({
        'bot_id': bot_id,
        'status': 'joined',
        'session_id': session_id
    })

@app.route('/bot/<bot_id>/leave', methods=['POST'])
def leave_meeting(bot_id):
    """Remove bot from meeting."""
    if bot_id in active_bots:
        bot = active_bots[bot_id]
        bot.sdk.leave_meeting()
        del active_bots[bot_id]

        return jsonify({'status': 'left'})

    return jsonify({'error': 'Bot not found'}), 404
```

**3. JWT Generation** (Required for SDK)
```python
import jwt
import time

def generate_zoom_sdk_jwt(meeting_number, role=0):
    """Generate SDK JWT for meeting join."""
    payload = {
        'appKey': os.getenv('ZOOM_SDK_KEY'),
        'sdkKey': os.getenv('ZOOM_SDK_KEY'),
        'mn': meeting_number,
        'role': role,  # 0 = participant, 1 = host
        'iat': int(time.time()),
        'exp': int(time.time()) + 7200,  # 2 hours
        'tokenExp': int(time.time()) + 7200
    }

    token = jwt.encode(
        payload,
        os.getenv('ZOOM_SDK_SECRET'),
        algorithm='HS256'
    )

    return token
```

**4. Integration with Main App**
```python
# In your main frontend/backend

async function startZoomBrainstorm(meetingId, password) {
  // 1. Create session
  const sessionRes = await fetch('/sessions/start', { method: 'POST' })
  const { session_id } = await sessionRes.json()

  // 2. Deploy bot
  const botRes = await fetch('http://localhost:8010/bot/join', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      meeting_id: meetingId,
      password: password,
      session_id: session_id
    })
  })

  const { bot_id } = await botRes.json()

  // 3. Connect to transcript stream
  const eventSource = new EventSource(`/sessions/${session_id}/stream`)
  eventSource.onmessage = (event) => {
    const chunk = JSON.parse(event.data)
    // Update UI with transcript
  }

  return { session_id, bot_id }
}
```

#### Deployment Requirements

**Infrastructure:**
- Linux/Windows/Mac server (not cloud functions)
- Desktop environment (X11 for Linux)
- Sufficient CPU/RAM for Zoom client
- One server per bot (or VM/container per bot)

**Scaling:**
- Docker containers per bot instance
- Kubernetes for orchestration
- Auto-scaling based on demand

**Example Docker Setup:**
```dockerfile
FROM ubuntu:22.04

# Install Zoom SDK dependencies
RUN apt-get update && apt-get install -y \
    python3 python3-pip \
    libx11-6 libxcb1 libxcomposite1 \
    pulseaudio \
    # ... other dependencies

# Copy bot code
COPY zoom-bot/ /app/
WORKDIR /app

# Install Python dependencies
RUN pip3 install -r requirements.txt

# Run bot manager
CMD ["python3", "meeting_manager.py"]
```

#### Pros & Cons

✅ **Pros:**
- Full control over audio/video
- Per-speaker audio streams (perfect diarization)
- Highest quality audio
- No external API dependencies
- Can process video if needed
- Most flexibility

❌ **Cons:**
- Extremely complex implementation
- Requires desktop/server environment
- Complex deployment (Docker/K8s)
- Bot visible in meeting
- SDK licensing considerations
- Must maintain bot infrastructure
- Scaling is challenging
- Zoom SDK has learning curve

#### Best For
- Enterprise deployments
- When per-speaker separation is critical
- Need full control and no external dependencies
- Have DevOps resources
- Long-term product with dedicated team

---

## Technical Requirements

### Common Requirements (All Options)

#### 1. Session-Meeting Association

Update `session_manager.py` to track meeting metadata:

```python
from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class Session:
    session_id: str
    started_at: str
    status: str = "active"
    full_transcript: str = ""
    chunks: List[TranscriptChunk] = field(default_factory=list)
    chunk_count: int = 0
    total_duration: float = 0.0
    last_chunk_text: str = ""
    metadata: Dict = field(default_factory=dict)

    # NEW: Meeting integration fields
    meeting_id: Optional[str] = None
    meeting_platform: Optional[str] = None  # "zoom", "meet", "teams", "local"
    meeting_url: Optional[str] = None
    bot_id: Optional[str] = None  # For bot-based approaches
    meeting_participants: List[str] = field(default_factory=list)
    audio_source: str = "microphone"  # "microphone", "system", "bot", "api"
```

#### 2. Multi-Speaker Support (Future Enhancement)

For per-speaker transcription:

```python
@dataclass
class TranscriptChunk:
    chunk_id: int
    text: str
    timestamp: str
    confidence: Optional[float] = None
    duration_ms: Optional[int] = None

    # NEW: Speaker identification
    speaker_id: Optional[str] = None
    speaker_name: Optional[str] = None
    speaker_email: Optional[str] = None
```

Update graph generation to show who said what:
```json
{
  "nodes": [
    {
      "id": "concept-1",
      "label": "User Experience",
      "type": "concept",
      "metadata": {
        "mentioned_by": ["speaker-1", "speaker-3"],
        "first_mentioned_at": "2025-11-01T10:30:45Z"
      }
    }
  ]
}
```

#### 3. Environment Configuration

**For Desktop Audio (Option 1):**
```env
# No new env vars needed!
```

**For Recall.ai (Option 2):**
```env
RECALL_API_KEY=your-recall-api-key
RECALL_WEBHOOK_SECRET=your-webhook-secret
PUBLIC_WEBHOOK_URL=https://yourapp.com/recall/webhook
```

**For Zoom Apps (Option 3):**
```env
ZOOM_CLIENT_ID=your-client-id
ZOOM_CLIENT_SECRET=your-client-secret
ZOOM_REDIRECT_URI=https://yourapp.com/auth/zoom/callback
```

**For Zoom SDK (Option 4):**
```env
ZOOM_SDK_KEY=your-sdk-key
ZOOM_SDK_SECRET=your-sdk-secret
BOT_MANAGER_URL=http://localhost:8010
```

#### 4. Frontend Changes

**Meeting Join UI:**
```typescript
// components/MeetingJoin.tsx
import { useState } from 'react'

export default function MeetingJoin() {
  const [meetingUrl, setMeetingUrl] = useState('')
  const [audioSource, setAudioSource] = useState('microphone')

  const startSession = async () => {
    if (audioSource === 'microphone' || audioSource === 'system') {
      // Desktop audio capture
      const devices = await fetch('/audio/devices').then(r => r.json())
      // Show device selector...

    } else if (audioSource === 'bot') {
      // Recall.ai or Zoom SDK bot
      const response = await fetch('/api/zoom/join', {
        method: 'POST',
        body: JSON.stringify({ meeting_url: meetingUrl })
      })

      const { session_id } = await response.json()
      // Connect to stream...
    }
  }

  return (
    <div>
      <h2>Join Meeting</h2>

      <select value={audioSource} onChange={e => setAudioSource(e.target.value)}>
        <option value="microphone">Local Microphone</option>
        <option value="system">System Audio (Virtual Cable)</option>
        <option value="bot">Meeting Bot (Zoom/Meet/Teams)</option>
      </select>

      {audioSource === 'bot' && (
        <input
          type="text"
          placeholder="Meeting URL"
          value={meetingUrl}
          onChange={e => setMeetingUrl(e.target.value)}
        />
      )}

      <button onClick={startSession}>Start Brainstorming</button>
    </div>
  )
}
```

---

## Code Changes Required

### Option 1: Desktop Audio (Minimal Changes)

**Files to Modify:**
1. ✏️ `speech-to-text/src/audio_capture.py` - Add `device_index` parameter
2. ✏️ `speech-to-text/src/main.py` - Add `/audio/devices` endpoint
3. ➕ `frontend/components/DeviceSelector.tsx` - New device picker UI

**Total Lines of Code:** ~100 lines
**Files Changed:** 2 existing, 1 new
**Existing Pipeline:** 100% compatible

---

### Option 2: Recall.ai (Moderate Changes)

**Files to Add:**
1. ➕ `zoom-integration/recall_client.py` - API wrapper (~80 lines)
2. ➕ `zoom-integration/recall_webhook.py` - Webhook handler (~120 lines)
3. ➕ `frontend/components/BotControls.tsx` - Bot UI (~60 lines)

**Files to Modify:**
1. ✏️ `speech-to-text/src/main.py` - Add `/transcribe/stream/<session_id>` endpoint (~30 lines)
2. ✏️ `speech-to-text/src/session_manager.py` - Add meeting fields to `Session` class (~15 lines)
3. ✏️ `frontend/app/page.tsx` - Integrate bot controls (~40 lines)

**Total Lines of Code:** ~345 lines
**Files Changed:** 3 existing, 3 new
**Existing Pipeline:** 95% compatible (just add streaming endpoint)

---

### Option 3: Zoom Apps (Significant Changes)

**New Directory Structure:**
```
zoom-app/
├── package.json
├── src/
│   ├── App.tsx              # Main Zoom App component
│   ├── components/
│   │   ├── GraphView.tsx
│   │   └── Controls.tsx
│   ├── hooks/
│   │   └── useZoomSDK.ts
│   └── utils/
│       └── auth.ts
├── public/
│   └── config.json
└── README.md
```

**Backend Changes:**
1. ➕ `backend/zoom_oauth.py` - OAuth flow (~200 lines)
2. ➕ `backend/zoom_app_api.py` - Zoom App backend endpoints (~150 lines)
3. ✏️ All Option 1 changes (for audio capture workaround)

**Total Lines of Code:** ~800 lines (Zoom App) + ~100 (audio workaround)
**Files Changed:** Multiple new directories
**Existing Pipeline:** Compatible with audio workaround

---

### Option 4: Zoom SDK Bot (Major Changes)

**New Component:**
```
zoom-bot/
├── bot.py                  # Main bot (~300 lines)
├── sdk_wrapper.py          # SDK interface (~400 lines)
├── audio_bridge.py         # Audio processing (~200 lines)
├── meeting_manager.py      # Bot API (~250 lines)
├── Dockerfile              # Deployment (~50 lines)
├── requirements.txt
└── README.md
```

**Backend Integration:**
1. ➕ `backend/bot_controller.py` - Bot lifecycle management (~150 lines)
2. ✏️ `speech-to-text/src/main.py` - Add streaming endpoint (~30 lines)
3. ✏️ `speech-to-text/src/session_manager.py` - Meeting metadata (~15 lines)

**Frontend:**
1. ➕ `frontend/components/BotMonitor.tsx` - Bot status UI (~100 lines)

**Total Lines of Code:** ~1,495 lines
**Files Changed:** Entire new component + integration
**Existing Pipeline:** Compatible (streams to existing endpoints)

---

## Recommendations

### Quick Start Path (This Week)

**Use Option 1: Desktop Audio Capture**

**Why:**
- ✅ Fastest implementation (1-2 days with AI assistance)
- ✅ Validates entire pipeline end-to-end
- ✅ Zero cost
- ✅ Minimal code changes (~100 lines)
- ✅ Works immediately

**Implementation Steps:**
1. Day 1 Morning: Add device selection to AudioCapture
2. Day 1 Afternoon: Add `/audio/devices` endpoint
3. Day 2 Morning: Build frontend device selector
4. Day 2 Afternoon: Test with real Zoom meeting, iterate

**Deliverable:** Working demo showing live graph generation from Zoom meetings

---

### Production Path (Next 2-3 Weeks)

**Use Option 2: Recall.ai Bot Service**

**Why:**
- ✅ Production-grade reliability
- ✅ No user setup required
- ✅ Scales to many meetings
- ✅ Works with Zoom, Meet, Teams
- ✅ Per-speaker audio (perfect diarization)
- ✅ Moderate complexity with AI assistance
- ✅ Reasonable cost ($0.70-1.24/hour)

**Implementation Steps:**

**Week 1: Core Integration**
- Day 1-2: Implement Recall.ai client wrapper
- Day 3: Build webhook handler
- Day 4-5: Update session manager with meeting metadata
- Test: Bot joins meeting, audio flows to transcription

**Week 2: Frontend & Features**
- Day 1-2: Build meeting join UI
- Day 3: Add bot status monitoring
- Day 4-5: Per-speaker identification (if needed)
- Test: Full user flow

**Week 3: Polish & Deploy**
- Day 1-2: Error handling, edge cases
- Day 3-4: Deploy webhook endpoint, test production
- Day 5: Documentation, demo prep

**Deliverable:** Production-ready Zoom integration

---

### Long-term Strategy (If Building SaaS)

**Phase 1 (Month 1-2):** Option 2 (Recall.ai)
- Get to market quickly
- Validate product-market fit
- Gather user feedback

**Phase 2 (Month 3-4):** Option 3 (Zoom Apps)
- Build native Zoom App for better UX
- Keep Recall.ai for audio capture
- Publish to Zoom Marketplace

**Phase 3 (Month 5-6+):** Option 4 (Zoom SDK) - If needed
- Only if per-speaker audio is critical
- Only if API costs become prohibitive (high volume)
- Only if have DevOps resources

---

## Effort Estimates (AI-Assisted Development)

With modern AI coding assistants (Claude Code, Cursor, GitHub Copilot, etc.):

| Option | Solo Developer | Small Team (2-3) | Complexity |
|--------|---------------|------------------|------------|
| **1. Desktop Audio** | 1-2 days | 1 day | Low ⭐ |
| **2. Recall.ai Bot** | 1-2 weeks | 1 week | Medium ⭐⭐ |
| **3. Zoom Apps SDK** | 3-4 weeks | 2 weeks | High ⭐⭐⭐ |
| **4. Zoom SDK Bot** | 4-6 weeks | 2-3 weeks | Very High ⭐⭐⭐⭐ |

**Assumptions:**
- Developer familiar with Python/TypeScript
- Using AI coding assistant for boilerplate
- Has access to Zoom/API accounts
- Working codebase (already have this ✅)

**What AI Assistants Accelerate:**
- ✅ Boilerplate code (API wrappers, webhooks) - 70% faster
- ✅ Data structure transformations - 60% faster
- ✅ Error handling patterns - 50% faster
- ✅ Documentation - 80% faster
- ⚠️ Architecture decisions - Still need human judgment
- ⚠️ Debugging complex integration issues - AI helps, but slower

**What Still Takes Time:**
- OAuth flows and security (need careful review)
- Deployment and DevOps setup
- Testing with real Zoom meetings
- Edge case handling
- Zoom's approval process (for Apps/Marketplace)

---

## Decision Matrix

### Choose Desktop Audio (Option 1) If:
- ✅ Building MVP/prototype
- ✅ Personal use or internal tool
- ✅ Need results this week
- ✅ Budget is $0
- ✅ Comfortable with user setup

### Choose Recall.ai (Option 2) If:
- ✅ Building production SaaS
- ✅ Need multi-platform (Zoom + Meet + Teams)
- ✅ Want per-speaker identification
- ✅ Have budget (~$1/hour per meeting)
- ✅ Want to move fast but production-ready
- ⭐ **RECOMMENDED FOR MOST CASES**

### Choose Zoom Apps (Option 3) If:
- ✅ Committed to Zoom ecosystem only
- ✅ UX is critical differentiator
- ✅ Willing to wait for marketplace approval
- ✅ Have 3-4 weeks for development
- ✅ Want professional "native" appearance

### Choose Zoom SDK Bot (Option 4) If:
- ✅ Enterprise deployment with dedicated DevOps
- ✅ Per-speaker audio is absolutely critical
- ✅ High meeting volume (API costs > server costs)
- ✅ Need full control over all aspects
- ✅ Have 6+ weeks and engineering resources

---

## Next Steps

### Immediate Action (This Week)

1. **Validate with Desktop Audio**
   ```bash
   cd speech-to-text
   git checkout -b feature/zoom-audio-capture
   # Implement Option 1 changes
   # Test with real Zoom meeting
   ```

2. **Test Full Pipeline**
   - Join Zoom meeting
   - Route audio through virtual cable
   - Verify transcription works
   - Verify graph generation works
   - Document any issues

3. **Demo & Decide**
   - Show working prototype
   - Gather feedback
   - Decide on production approach (likely Option 2)

### Short-term (Next 2 Weeks)

If going with Recall.ai:

1. **Week 1**: Core integration
   - Sign up for Recall.ai
   - Implement client wrapper
   - Build webhook handler
   - Test bot joining meeting

2. **Week 2**: Frontend & Testing
   - Build meeting join UI
   - End-to-end testing
   - Error handling
   - Documentation

### Medium-term (Month 2-3)

- Deploy to production
- Monitor costs and performance
- Gather user feedback
- Consider Zoom App for better UX (Option 3)

---

## Resources & Documentation

### Zoom API Documentation
- Zoom Developer Platform: https://developers.zoom.us/
- Meeting SDK Docs: https://developers.zoom.us/docs/meeting-sdk/
- Zoom Apps SDK: https://developers.zoom.us/docs/zoom-apps/
- OAuth Guide: https://developers.zoom.us/docs/integrations/oauth/

### Recall.ai Documentation
- API Reference: https://www.recall.ai/docs
- Bot API Guide: https://www.recall.ai/docs/bot-api
- Webhooks: https://www.recall.ai/docs/webhooks
- Pricing: https://www.recall.ai/pricing

### Virtual Audio Cables
- **macOS**: Blackhole - https://existential.audio/blackhole/
- **Windows**: VB-Cable - https://vb-audio.com/Cable/
- **Linux**: PulseAudio Loopback - https://wiki.archlinux.org/title/PulseAudio/Examples

### Existing Codebase
- Speech-to-Text: `/speech-to-text/src/`
- Graph Generation: `/graph-generation/`
- Architecture Docs: `/docs/architecture.md`
- Integration Guide: `/docs/integration.md`

---

## FAQ

**Q: Can we use the same pipeline for Google Meet and Microsoft Teams?**
A: Yes! Option 1 (desktop audio) and Option 2 (Recall.ai) work with all platforms. Options 3 & 4 are Zoom-specific.

**Q: What about speaker identification (who said what)?**
A: Option 2 (Recall.ai) and Option 4 (Zoom SDK) provide per-speaker audio streams. Options 1 & 3 require post-processing diarization (pyannote, AssemblyAI, etc.)

**Q: Can we run this in the browser?**
A: Partially. Desktop audio capture requires native app. Recall.ai bot can work with browser frontend. Zoom SDK bot requires server.

**Q: How much will this cost at scale?**
A:
- Option 1: $0 (but doesn't scale)
- Option 2: $0.70-1.24/hr per meeting
- Option 3: $0 + user setup
- Option 4: Server costs (~$20-50/month per bot instance)

**Q: How long does it take Zoom to approve apps?**
A: 2-4 weeks typically for Zoom Apps marketplace submission.

**Q: Can we record meetings automatically?**
A: Yes with Options 2 & 4 (bots can record). Options 1 & 3 require separate recording setup.

**Q: What about privacy and consent?**
A: Bot-based approaches (2 & 4) show visible bot participant. Must comply with recording consent laws. Desktop audio (1) is personal device capture only.

---

## Summary

### Your Current System is Ready ✅

Your existing speech-to-text pipeline is production-ready and well-architected. The Zoom integration challenge is simply: **getting audio into your pipeline**.

### Recommended Approach

**Week 1**: Build Option 1 (Desktop Audio) for quick validation
**Week 2-3**: Implement Option 2 (Recall.ai) for production
**Month 2+**: Consider Option 3 (Zoom Apps) for better UX if product-market fit is validated

### Key Insight

95% of your existing code remains unchanged. The integration is primarily about:
1. Audio routing/capture (new)
2. Session-meeting association (small change)
3. Frontend meeting join UI (new)

Your `AudioBuffer`, `TranscriptionService`, `SessionManager`, and graph generation components work as-is!

---

**Document Version**: 1.0
**Last Updated**: November 2025
**Maintained By**: Development Team
**Questions?**: See `/docs/integration.md` or create an issue
