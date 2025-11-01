# Pause/Resume Feature - Implementation Plan

## Overview

Add the ability to **pause** and **resume** active sessions without losing state, allowing users to:
- Temporarily stop audio capture and transcription
- Maintain current graph and session state
- Resume from exactly where they left off
- **Future:** Perform AI operations on the graph while paused (e.g., generate ideas, analyze nodes)

---

## Current Architecture

### Session Lifecycle (Current)

```
Start → Active → Stop (with grace period) → Saved to disk
```

### Proposed Session Lifecycle

```
Start → Active ←→ Paused → Resume → Active
                     ↓
                  Stop → Saved to disk
```

---

## Current Flow Analysis

### 1. **STT Service** (Port 8005)

**File:** `speech-to-text/src/session_manager.py`

**Current Session Statuses:**
```python
status: str = "active"  # active, stopped, error
```

**Stream Loop (main.py line 155):**
```python
while session.status == 'active':
    # Capture audio every ~8 seconds
    # Transcribe
    # Emit to orchestrator
```

**Issue:** Loop only checks for `'active'`, exits if status changes.

---

### 2. **Orchestrator Service** (Port 8003)

**File:** `orchestrator/src/session_orchestrator.py`

**Current Session Statuses:**
```python
'status': 'created'  # created, active, stopped
```

**Stream Check (main.py line 257):**
```python
if session['status'] != 'active':
    return error
```

**Issue:** Rejects SSE stream connection if not 'active'.

---

### 3. **Frontend**

**File:** `frontend/live-graph/js/session-manager.js`

**Current Methods:**
- `startSession()` - Create and start
- `stopSession()` - Stop with grace period

**Issue:** No pause/resume methods.

---

## Implementation Plan

### Phase 1: Core Pause/Resume (No Breaking Changes)

#### 1.1 STT Service Changes

**File:** `speech-to-text/src/session_manager.py`

**Changes:**
1. Update Session class status options:
   ```python
   status: str = "active"  # active, paused, stopped, error
   ```

2. Add pause/resume methods to SessionManager:
   ```python
   def pause_session(self, session_id: str) -> Dict[str, Any]:
       """Pause a session - stops audio capture but keeps state."""
       # Set status = 'paused'
       # Stop audio buffer from capturing
       # Keep session in memory

   def resume_session(self, session_id: str) -> Dict[str, Any]:
       """Resume a paused session - continues from current state."""
       # Set status = 'active'
       # Resume audio buffer capture
   ```

3. Modify stream loop in `main.py`:
   ```python
   while session.status in ['active', 'paused']:
       if session.status == 'active':
           # Normal processing
       elif session.status == 'paused':
           # Wait and check again (don't capture audio)
           time.sleep(0.5)
           continue
   ```

**New Endpoints:**
- `POST /sessions/<id>/pause` - Pause session
- `POST /sessions/<id>/resume` - Resume session

---

#### 1.2 Orchestrator Service Changes

**File:** `orchestrator/src/session_orchestrator.py`

**Changes:**
1. Update session status options:
   ```python
   'status': 'created'  # created, active, paused, stopped
   ```

2. Add pause/resume methods:
   ```python
   def pause_session(self, session_id: str) -> Dict[str, Any]:
       """Pause a session."""
       # Set status = 'paused'
       # Record paused_at timestamp
       # Keep graph and transcript in memory

   def resume_session(self, session_id: str) -> Dict[str, Any]:
       """Resume a paused session."""
       # Set status = 'active'
       # Record resumed_at timestamp
       # Continue with existing graph as base
   ```

3. Modify SSE stream check in `main.py`:
   ```python
   if session['status'] not in ['active', 'paused']:
       return error
   ```

4. Add metadata tracking:
   ```python
   'metadata': {
       'paused_at': None,
       'resumed_at': None,
       'pause_count': 0,
       'total_paused_duration': 0  # seconds
   }
   ```

**New Endpoints:**
- `POST /sessions/<id>/pause` - Pause session (proxies to STT)
- `POST /sessions/<id>/resume` - Resume session (proxies to STT)

**File:** `orchestrator/src/main.py`

**Implementation:**
```python
@app.route('/sessions/<session_id>/pause', methods=['POST'])
def pause_session(session_id: str):
    """Pause a session - stops audio capture."""
    try:
        # Check session exists and is active
        session = orchestrator.get_session(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404

        if session['status'] != 'active':
            return jsonify({'error': 'Can only pause active sessions'}), 400

        # Pause STT session
        stt_response = requests.post(
            f"{STT_SERVICE_URL}/sessions/{session_id}/pause",
            json={},
            timeout=5
        )

        if stt_response.status_code == 200:
            # Update orchestrator session
            result = orchestrator.pause_session(session_id)
            return jsonify(result), 200
        else:
            return jsonify({'error': 'Failed to pause STT'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/sessions/<session_id>/resume', methods=['POST'])
def resume_session(session_id: str):
    """Resume a paused session."""
    # Similar to pause, but checks status == 'paused'
```

---

#### 1.3 Frontend Changes

**File:** `frontend/live-graph/js/session-manager.js`

**New Methods:**
```javascript
async pauseSession() {
  if (!this.sessionId || this.isActive === false) {
    throw new Error('No active session to pause');
  }

  try {
    this._updateStatus('pausing', 'Pausing session...');

    const response = await fetch(
      `${this.orchestratorUrl}/sessions/${this.sessionId}/pause`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      }
    );

    if (!response.ok) {
      throw new Error(`Failed to pause: ${response.status}`);
    }

    const data = await response.json();
    this.isActive = false;
    this.isPaused = true;

    this._updateStatus('paused', 'Session paused');
    this.onStatusChange('paused', 'Session paused');

    return data;

  } catch (error) {
    this.onError(error);
    throw error;
  }
}

async resumeSession() {
  if (!this.sessionId || this.isPaused === false) {
    throw new Error('No paused session to resume');
  }

  try {
    this._updateStatus('resuming', 'Resuming session...');

    const response = await fetch(
      `${this.orchestratorUrl}/sessions/${this.sessionId}/resume`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      }
    );

    if (!response.ok) {
      throw new Error(`Failed to resume: ${response.status}`);
    }

    const data = await response.json();
    this.isActive = true;
    this.isPaused = false;

    this._updateStatus('active', 'Session resumed');
    this.onStatusChange('active', 'Session resumed - receiving updates');

    return data;

  } catch (error) {
    this.onError(error);
    throw error;
  }
}
```

**File:** `frontend/live-graph/index.html`

**UI Changes:**
```html
<!-- Update live-buttons section -->
<div class="live-buttons">
  <button class="btn-success" id="start-live-session">Start Live Session</button>
  <button class="btn-warning" id="pause-live-session" disabled>Pause Session</button>
  <button class="btn-success" id="resume-live-session" disabled style="display: none;">Resume Session</button>
  <button class="btn-danger" id="stop-live-session" disabled>Stop Session</button>
</div>
```

**JavaScript handlers:**
```javascript
async function pauseLiveSession() {
  try {
    updateLiveStatus('Pausing...', false);

    const result = await sessionManager.pauseSession();

    // Update UI
    document.getElementById('pause-live-session').style.display = 'none';
    document.getElementById('resume-live-session').style.display = 'inline-block';
    document.getElementById('resume-live-session').disabled = false;

    updateLiveStatus('Paused', false);

  } catch (error) {
    alert(`Failed to pause: ${error.message}`);
  }
}

async function resumeLiveSession() {
  try {
    updateLiveStatus('Resuming...', true);

    const result = await sessionManager.resumeSession();

    // Update UI
    document.getElementById('resume-live-session').style.display = 'none';
    document.getElementById('pause-live-session').style.display = 'inline-block';
    document.getElementById('pause-live-session').disabled = false;

    updateLiveStatus('Active - receiving updates', true);

  } catch (error) {
    alert(`Failed to resume: ${error.message}`);
  }
}
```

---

## SSE Connection Strategy

### Option A: Keep SSE Open During Pause (Recommended)

**Pros:**
- Simpler implementation
- No reconnection logic needed
- Instant resume
- Graph stays in sync

**Cons:**
- Idle connection during pause
- Potential proxy timeout (mitigated by keepalive)

**Implementation:**
- SSE stream stays connected
- STT just stops emitting events when paused
- On resume, events start flowing again
- Frontend graph renderer just waits for next update

### Option B: Close SSE During Pause

**Pros:**
- No idle connections
- Clean separation

**Cons:**
- Need reconnection logic
- Potential state sync issues
- More complex error handling

**Recommendation:** Go with **Option A** for simplicity.

---

## Future Features (Phase 2)

### AI-Assisted Graph Enhancement While Paused

When session is paused, enable additional operations:

#### 2.1 New Orchestrator Endpoints

```python
@app.route('/sessions/<session_id>/ai-suggestions', methods=['POST'])
def generate_ai_suggestions(session_id: str):
    """
    Generate AI suggestions for the current graph.
    Only works when session is paused.
    """
    session = orchestrator.get_session(session_id)

    if session['status'] != 'paused':
        return jsonify({'error': 'Session must be paused'}), 400

    current_graph = session['graph']

    # Call graph-generation with special mode
    suggestions = requests.post(
        f"{GRAPH_SERVICE_URL}/suggest-ideas",
        json={
            'graph': current_graph,
            'mode': 'expand'  # or 'connect', 'refine', etc.
        }
    )

    return jsonify(suggestions.json())

@app.route('/sessions/<session_id>/graph/modify', methods=['POST'])
def modify_graph(session_id: str):
    """
    Manually modify the graph while paused.
    Accepts: add_node, remove_node, add_edge, remove_edge
    """
    # Allow manual graph manipulation
```

#### 2.2 Frontend "Paused Mode" Panel

```html
<div class="paused-actions" id="paused-mode-panel" style="display: none;">
  <h4>Paused - AI Actions</h4>
  <button class="btn-primary" id="ai-expand-ideas">💡 Generate New Ideas</button>
  <button class="btn-primary" id="ai-find-connections">🔗 Find Hidden Connections</button>
  <button class="btn-primary" id="ai-summarize">📝 Summarize Discussion</button>
  <button class="btn-primary" id="ai-questions">❓ Generate Questions</button>
</div>
```

**AI Actions:**
- **Generate New Ideas:** Expand nodes with related concepts
- **Find Connections:** Suggest edges between unconnected nodes
- **Summarize:** Create summary node of main themes
- **Generate Questions:** Add question nodes for unexplored areas

---

## Data Flow Diagrams

### Normal Active Session
```
User speaks → Microphone → STT capture → Transcribe → Orchestrator → Graph Gen → Frontend
                                ↓                           ↓
                          Save to buffer              Update graph state
                                ↓                           ↓
                          Emit every 8s               Continue with previous graph
```

### Paused Session
```
User pauses → STT stops capturing → Orchestrator marks 'paused' → Frontend shows "Paused"
                      ↓
            Audio buffer preserved
            Session state maintained
            Graph preserved in memory
                      ↓
            [Optional: AI operations on graph]
                      ↓
User resumes → STT starts capturing → Orchestrator marks 'active' → Frontend shows "Active"
                      ↓
            Continue from current graph
```

---

## Benefits

### 1. **User Experience**
- Pause for phone calls, interruptions
- Think before continuing
- Review graph before adding more
- No need to stop and restart (which loses context)

### 2. **AI Enhancement**
- AI can analyze and enhance graph while paused
- User can review AI suggestions
- Accept/reject AI additions before resuming
- Hybrid human+AI brainstorming

### 3. **Session Management**
- Track pause duration in metadata
- Understand session patterns
- Better analytics (active time vs total time)

### 4. **Future Extensibility**
- Pause to export graph
- Pause to share with collaborators
- Pause to switch topics
- Multiple pause/resume cycles

---

## Implementation Checklist

### Phase 1: Core Pause/Resume

- [ ] **STT Service**
  - [ ] Add 'paused' status to Session class
  - [ ] Implement pause_session() method
  - [ ] Implement resume_session() method
  - [ ] Add POST /sessions/<id>/pause endpoint
  - [ ] Add POST /sessions/<id>/resume endpoint
  - [ ] Modify stream loop to handle 'paused' state
  - [ ] Add tests for pause/resume

- [ ] **Orchestrator Service**
  - [ ] Add 'paused' status to session state
  - [ ] Implement pause_session() method
  - [ ] Implement resume_session() method
  - [ ] Add POST /sessions/<id>/pause endpoint
  - [ ] Add POST /sessions/<id>/resume endpoint
  - [ ] Add pause metadata tracking
  - [ ] Modify SSE stream check to allow 'paused'
  - [ ] Add tests for pause/resume

- [ ] **Frontend**
  - [ ] Add isPaused state to SessionManager
  - [ ] Implement pauseSession() method
  - [ ] Implement resumeSession() method
  - [ ] Add Pause button to UI
  - [ ] Add Resume button to UI
  - [ ] Handle paused state in status indicator
  - [ ] Update button visibility logic
  - [ ] Test pause/resume flow

### Phase 2: AI Enhancements (Future)

- [ ] **Graph Service**
  - [ ] Add /suggest-ideas endpoint
  - [ ] Add /find-connections endpoint
  - [ ] Add /summarize endpoint

- [ ] **Orchestrator**
  - [ ] Add /sessions/<id>/ai-suggestions endpoint
  - [ ] Add /sessions/<id>/graph/modify endpoint

- [ ] **Frontend**
  - [ ] Add paused-mode panel
  - [ ] Implement AI action buttons
  - [ ] Add graph modification UI

---

## Risks & Considerations

### 1. **Audio Buffer Handling**
**Issue:** What happens to buffered audio when pausing?

**Options:**
- **A.** Discard buffer (recommended - clean pause)
- **B.** Process buffer before pausing (could delay pause)
- **C.** Keep buffer and process on resume (might be confusing)

**Recommendation:** Discard buffer on pause for clean separation.

### 2. **SSE Timeout**
**Issue:** Some proxies timeout idle connections

**Mitigation:**
- Send keepalive heartbeat every 30s even when paused
- Or close and reconnect on resume (Option B)

### 3. **Multiple Pause/Resume Cycles**
**Issue:** Graph could get very large with many cycles

**Mitigation:**
- Track pause_count in metadata
- Warn if session becomes too large
- Option to "finalize and start new session"

### 4. **State Consistency**
**Issue:** Ensuring orchestrator and STT stay in sync

**Mitigation:**
- Always proxy pause/resume through orchestrator
- Orchestrator checks STT status before updating its own
- Add health check to verify state consistency

---

## Testing Plan

### Unit Tests
- [ ] STT pause/resume state transitions
- [ ] Orchestrator pause/resume state transitions
- [ ] SessionManager pause/resume methods

### Integration Tests
- [ ] Full pause/resume flow (STT → Orchestrator → Frontend)
- [ ] Multiple pause/resume cycles
- [ ] Pause → Stop → Session saved correctly
- [ ] Resume continues with correct graph state

### Manual Tests
- [ ] Pause during active transcription
- [ ] Resume after 10s, 1min, 5min
- [ ] Speak → Pause → Resume → Speak → Verify continuity
- [ ] Check final session file includes pause metadata

---

## Summary

**Pause/Resume is a clean, non-breaking addition** that:

✅ Adds new 'paused' status to both STT and Orchestrator
✅ Keeps SSE connection open (simple approach)
✅ Maintains all state (graph, transcript, session)
✅ Enables future AI features while paused
✅ Improves user experience significantly
✅ No changes to existing start/stop logic

**Implementation Order:**
1. STT Service (pause/resume methods + endpoints)
2. Orchestrator Service (pause/resume proxies + state management)
3. Frontend (UI buttons + SessionManager methods)
4. Testing (unit + integration + manual)
5. Future: AI enhancement features

**Estimated Effort:**
- Phase 1 (Core): ~4-6 hours of development + testing
- Phase 2 (AI): ~8-10 hours (can be done later)

Ready to implement when you are! 🚀
