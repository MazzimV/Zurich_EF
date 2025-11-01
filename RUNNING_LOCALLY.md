# Running the Brainstorm Graph Project Locally

Complete guide to run the entire real-time brainstorming system on your local machine.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Project Architecture](#project-architecture)
3. [Setup Instructions](#setup-instructions)
   - [Speech-to-Text Service](#1-speech-to-text-service-port-8005)
   - [Graph Generation Service](#2-graph-generation-service-port-8002)
   - [Orchestrator Service](#3-orchestrator-service-port-8003)
   - [Frontend](#4-frontend-port-8080)
4. [Running the Full System](#running-the-full-system)
5. [Verification](#verification)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

- **Python 3.12+** ([Download](https://www.python.org/downloads/))
- **Git** ([Download](https://git-scm.com/downloads))
- **Web Browser** (Chrome, Firefox, Safari, or Edge)

### Required API Keys

You'll need the following API keys:

1. **OpenAI API Key** - For speech-to-text transcription
   - Get it from: https://platform.openai.com/api-keys
   - You'll need credits on your OpenAI account

2. **Anthropic API Key** - For Claude AI (graph generation)
   - Get it from: https://console.anthropic.com/
   - You'll need credits on your Anthropic account

---

## Project Architecture

The system consists of 4 components that work together:

```
┌─────────────┐
│  Frontend   │  Port 8080  (User Interface)
│  (HTML/JS)  │
└──────┬──────┘
       │
       ↓
┌─────────────┐
│Orchestrator │  Port 8003  (Coordination)
│  (Python)   │
└──┬────────┬─┘
   │        │
   ↓        ↓
┌──────┐ ┌────────┐
│ STT  │ │ Graph  │
│ 8005 │ │  8002  │
└──────┘ └────────┘
```

**Data Flow:**
1. User speaks → Frontend captures audio
2. Frontend → STT Service (transcribes every ~8 seconds)
3. STT → Orchestrator (sends transcript chunks)
4. Orchestrator → Graph Generation (sends transcript + previous graph)
5. Graph Generation → Orchestrator (returns updated graph)
6. Orchestrator → Frontend (SSE stream with transcript + graph)
7. Frontend displays real-time graph visualization

---

## Setup Instructions

### 1. Speech-to-Text Service (Port 8005)

**Location:** `speech-to-text/`

#### Step 1.1: Create Virtual Environment

```bash
cd speech-to-text
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### Step 1.2: Install Requirements

```bash
pip install -r requirements.txt
```

**Requirements include:**
- `openai` - OpenAI Python SDK
- `flask` - Web framework
- `flask-cors` - CORS support
- `python-dotenv` - Environment variable management

#### Step 1.3: Create Environment File

Create `speech-to-text/.env`:

```bash
# OpenAI API Configuration
OPENAI_API_KEY=sk-proj-XXXXXXXXXXXXXXXXXXXXXXXXXXXXX  # Your OpenAI API key
OPENAI_MODEL=gpt-4o-transcribe-diarize
TRANSCRIPTION_LANGUAGE=en

# Service Configuration
PORT=8005
DEBUG=false

# Session Configuration
MAX_SESSIONS=10
CHUNK_DURATION=8
```

**Important:** Replace `sk-proj-XXXXX` with your actual OpenAI API key!

#### Step 1.4: Run the Service

```bash
cd src
python3 main.py
```

**Expected output:**
```
============================================================
SPEECH-TO-TEXT SERVICE
============================================================
Port: 8005
Model: gpt-4o-transcribe-diarize
...
 * Running on http://0.0.0.0:8005
```

Keep this terminal open! ✅

---

### 2. Graph Generation Service (Port 8002)

**Location:** `graph-generation/segmentation/`

#### Step 2.1: Create Virtual Environment

```bash
cd graph-generation/segmentation
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### Step 2.2: Install Requirements

```bash
pip install -r requirements.txt
```

**Requirements include:**
- `anthropic` - Anthropic Claude SDK
- `flask` - Web framework
- `flask-cors` - CORS support
- `python-dotenv` - Environment variable management

#### Step 2.3: Create Environment File

Create `graph-generation/segmentation/.env`:

```bash
# Anthropic API Configuration
ANTHROPIC_API_KEY=sk-ant-api03-XXXXXXXXXXXXXXXXXXXXXXXXXXXXX  # Your Anthropic API key
LLM_MODEL=claude-sonnet-4-5-20250929

# Token Configuration
MAX_TOKENS=8192

# Service Configuration
PORT=8002
DEBUG=false
```

**Important:** Replace `sk-ant-api03-XXXXX` with your actual Anthropic API key!

#### Step 2.4: Run the Service

```bash
python3 main.py
```

**Expected output:**
```
============================================================
GRAPH GENERATION SERVICE
============================================================
Port: 8002
Model: claude-sonnet-4-5-20250929
...
 * Running on http://0.0.0.0:8002
```

Keep this terminal open! ✅

---

### 3. Orchestrator Service (Port 8003)

**Location:** `orchestrator/`

#### Step 3.1: Create Virtual Environment

```bash
cd orchestrator
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### Step 3.2: Install Requirements

```bash
pip install -r requirements.txt
```

**Requirements include:**
- `flask` - Web framework
- `flask-cors` - CORS support
- `requests` - HTTP client
- `python-dotenv` - Environment variable management

#### Step 3.3: Create Environment File

Create `orchestrator/.env`:

```bash
# Service URLs
STT_SERVICE_URL=http://localhost:8005
GRAPH_SERVICE_URL=http://localhost:8002

# Service Configuration
PORT=8003
DEBUG=false

# Session Configuration
MAX_SESSIONS=10
SAVE_DIRECTORY=./sessions
```

**Note:** The orchestrator doesn't need API keys - it just coordinates the other services!

#### Step 3.4: Run the Service

```bash
cd src
python3 main.py
```

**Expected output:**
```
============================================================
ORCHESTRATOR SERVICE
============================================================
Port: 8003
...
Speech-to-Text:    http://localhost:8005
Graph Generation:  http://localhost:8002
...
 * Running on http://0.0.0.0:8003
```

**The orchestrator will check if STT and Graph services are healthy on startup.**

Keep this terminal open! ✅

---

### 4. Frontend (Port 8080)

**Location:** `frontend/live-graph/`

#### Step 4.1: No Installation Required!

The frontend is pure HTML/CSS/JavaScript - no build process needed.

#### Step 4.2: Start HTTP Server

```bash
cd frontend/live-graph
python3 -m http.server 8080
```

**Expected output:**
```
Serving HTTP on 0.0.0.0 port 8080 (http://0.0.0.0:8080/) ...
```

#### Step 4.3: Open in Browser

Open your web browser and go to:
```
http://localhost:8080
```

You should see the **Live Graph Visualization** interface! ✅

---

## Running the Full System

### Quick Start Checklist

Open **4 terminal windows** and run these commands:

#### Terminal 1: Speech-to-Text
```bash
cd speech-to-text
source venv/bin/activate
cd src
python3 main.py
```

#### Terminal 2: Graph Generation
```bash
cd graph-generation/segmentation
source venv/bin/activate
python3 main.py
```

#### Terminal 3: Orchestrator
```bash
cd orchestrator
source venv/bin/activate
cd src
python3 main.py
```

#### Terminal 4: Frontend
```bash
cd frontend/live-graph
python3 -m http.server 8080
```

### All Services Running? ✅

You should have:
- ✅ Terminal 1: STT service on port 8005
- ✅ Terminal 2: Graph service on port 8002
- ✅ Terminal 3: Orchestrator on port 8003
- ✅ Terminal 4: Frontend on port 8080
- ✅ Browser open to http://localhost:8080

---

## Verification

### Test Each Service Individually

#### 1. Test Speech-to-Text (Port 8005)

```bash
curl http://localhost:8005/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "service": "speech_to_text",
  "model": "gpt-4o-transcribe-diarize"
}
```

#### 2. Test Graph Generation (Port 8002)

```bash
curl http://localhost:8002/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "service": "graph_generation",
  "model": "claude-sonnet-4-5-20250929"
}
```

#### 3. Test Orchestrator (Port 8003)

```bash
curl http://localhost:8003/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "service": "orchestrator",
  "dependencies": {
    "speech_to_text": {
      "healthy": true,
      "url": "http://localhost:8005"
    },
    "graph_generation": {
      "healthy": true,
      "url": "http://localhost:8002"
    }
  }
}
```

**If both dependencies show `"healthy": true`, you're good to go!** ✅

### Test the Frontend

1. Open http://localhost:8080
2. Click **"Live Mode (Orchestrator)"** tab
3. Click **"Check Health"** button
4. You should see: "Orchestrator is healthy" with ✅ for STT and Graph

---

## Using the System

### Step-by-Step Usage

1. **Open the frontend** at http://localhost:8080

2. **Switch to Live Mode**
   - Click the "Live Mode (Orchestrator)" tab

3. **Check Health**
   - Click "Check Health" to verify all services are running
   - Should show: STT ✅, Graph ✅

4. **Start a Session**
   - Click "Start Live Session"
   - Status will show "Connected - receiving updates"
   - Session ID will appear

5. **Start Speaking!**
   - Speak into your microphone
   - Every ~8 seconds:
     - Transcript appears in left panel
     - Graph updates in real-time
     - Nodes and edges appear with smooth animations

6. **Stop Session**
   - Click "Stop Session"
   - Grace period countdown (12 seconds) for final updates
   - Final summary shows total chunks and graph stats
   - Session saved to `orchestrator/sessions/`

---

## Troubleshooting

### Common Issues

#### Issue: "Port already in use"

**Problem:** Another process is using the port

**Solution:**
```bash
# Find what's using the port (replace 8005 with your port)
lsof -i :8005

# Kill the process
kill -9 <PID>
```

#### Issue: "OPENAI_API_KEY not set"

**Problem:** Missing or incorrect API key in `.env` file

**Solution:**
1. Check `.env` file exists in `speech-to-text/`
2. Verify API key is correct (starts with `sk-proj-` or `sk-`)
3. Make sure there are no spaces around the `=` sign
4. Restart the service

#### Issue: "ANTHROPIC_API_KEY not set"

**Problem:** Missing or incorrect API key in `.env` file

**Solution:**
1. Check `.env` file exists in `graph-generation/segmentation/`
2. Verify API key is correct (starts with `sk-ant-api03-`)
3. Make sure there are no spaces around the `=` sign
4. Restart the service

#### Issue: "Failed to connect to STT service"

**Problem:** STT service is not running

**Solution:**
1. Check Terminal 1 - is STT service running?
2. Verify it's on port 8005
3. Try `curl http://localhost:8005/health`

#### Issue: "Failed to connect to Graph service"

**Problem:** Graph service is not running

**Solution:**
1. Check Terminal 2 - is Graph service running?
2. Verify it's on port 8002
3. Try `curl http://localhost:8002/health`

#### Issue: "Health check shows STT/Graph as unhealthy"

**Problem:** Service is running but not responding correctly

**Solution:**
1. Check the service logs in the terminal
2. Look for error messages about API keys
3. Verify you have API credits available
4. Restart the problematic service

#### Issue: "No audio being captured"

**Problem:** Microphone permissions

**Solution:**
1. Check browser microphone permissions
2. Allow microphone access for localhost
3. Test microphone in browser settings
4. Try a different browser

#### Issue: "Graph not updating"

**Problem:** SSE connection issue or service error

**Solution:**
1. Check browser console (F12) for errors
2. Verify orchestrator logs show incoming chunks
3. Check graph-generation logs for errors
4. Try stopping and starting the session again

---

## File Structure Reference

```
brainstorm-graph/
├── speech-to-text/
│   ├── .env                    # ← API keys for OpenAI
│   ├── requirements.txt
│   ├── venv/                   # ← Virtual environment
│   └── src/
│       └── main.py             # ← Run this (port 8005)
│
├── graph-generation/
│   └── segmentation/
│       ├── .env                # ← API keys for Anthropic
│       ├── requirements.txt
│       ├── venv/               # ← Virtual environment
│       └── main.py             # ← Run this (port 8002)
│
├── orchestrator/
│   ├── .env                    # ← Service URLs (no API keys)
│   ├── requirements.txt
│   ├── venv/                   # ← Virtual environment
│   ├── sessions/               # ← Saved sessions appear here
│   └── src/
│       └── main.py             # ← Run this (port 8003)
│
└── frontend/
    └── live-graph/
        ├── index.html          # ← Open in browser
        ├── css/
        ├── js/
        └── test-data/
```

---

## Environment Variables Reference

### Speech-to-Text (.env)

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OPENAI_API_KEY` | Your OpenAI API key | - | ✅ Yes |
| `OPENAI_MODEL` | Transcription model | `gpt-4o-transcribe-diarize` | No |
| `PORT` | Service port | `8005` | No |
| `CHUNK_DURATION` | Seconds per chunk | `8` | No |

### Graph Generation (.env)

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key | - | ✅ Yes |
| `LLM_MODEL` | Claude model | `claude-sonnet-4-5-20250929` | No |
| `PORT` | Service port | `8002` | No |
| `MAX_TOKENS` | Max response tokens | `8192` | No |

### Orchestrator (.env)

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `STT_SERVICE_URL` | STT service URL | `http://localhost:8005` | No |
| `GRAPH_SERVICE_URL` | Graph service URL | `http://localhost:8002` | No |
| `PORT` | Service port | `8003` | No |
| `SAVE_DIRECTORY` | Session save path | `./sessions` | No |

---

## Tips & Best Practices

### 1. **Check Health Before Starting Sessions**
Always click "Check Health" in the frontend before starting a session to ensure all services are running.

### 2. **Monitor Service Logs**
Keep all terminal windows visible to monitor logs and catch errors early.

### 3. **API Credits**
Make sure you have sufficient credits on both OpenAI and Anthropic accounts. The system will fail silently if you run out of credits.

### 4. **Grace Period**
When stopping a session, wait for the 12-second grace period to complete. This ensures all spoken content is transcribed and graphed.

### 5. **Session Files**
Completed sessions are saved to `orchestrator/sessions/` as JSON files with timestamps. These contain the complete graph and transcript.

### 6. **Browser Console**
Keep browser console open (F12) to see detailed logs of SSE events and graph updates.

---

## Need Help?

- Check the logs in each terminal for error messages
- Verify all `.env` files are correctly configured
- Make sure all services are running before starting a session
- Try the health check endpoints individually
- Check that you have API credits available

**For issues or questions, create an issue on the project repository.**

---

## Quick Command Reference

```bash
# Start all services (4 terminals)
# Terminal 1
cd speech-to-text && source venv/bin/activate && cd src && python3 main.py

# Terminal 2
cd graph-generation/segmentation && source venv/bin/activate && python3 main.py

# Terminal 3
cd orchestrator && source venv/bin/activate && cd src && python3 main.py

# Terminal 4
cd frontend/live-graph && python3 -m http.server 8080
```

Then open http://localhost:8080 in your browser!

Happy brainstorming! 🚀
