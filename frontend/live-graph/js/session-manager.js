/**
 * Session Manager - Handles live orchestrator connections
 *
 * Manages session lifecycle and SSE streaming from the orchestrator service
 */

class SessionManager {
  constructor(orchestratorUrl, options = {}) {
    this.orchestratorUrl = orchestratorUrl;
    this.sessionId = null;
    this.eventSource = null;
    this.isConnected = false;
    this.isActive = false;
    this.isStopping = false;
    this.gracePeriodTimer = null;

    // Configuration
    this.gracePeriodSeconds = options.gracePeriodSeconds || 12;  // Wait for final updates

    // Callbacks
    this.onUpdate = options.onUpdate || (() => {});
    this.onError = options.onError || (() => {});
    this.onConnect = options.onConnect || (() => {});
    this.onDisconnect = options.onDisconnect || (() => {});
    this.onStatusChange = options.onStatusChange || (() => {});

    console.log('SessionManager initialized with URL:', orchestratorUrl);
  }

  /**
   * Start a new session
   * @returns {Promise<Object>} Session info
   */
  async startSession() {
    try {
      this._updateStatus('starting', 'Starting session...');
      console.log('🚀 Starting new session...');

      // Call orchestrator to start session
      const response = await fetch(`${this.orchestratorUrl}/sessions/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({})
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to start session: ${response.status} - ${errorText}`);
      }

      const sessionData = await response.json();
      this.sessionId = sessionData.session_id;

      console.log('✅ Session started:', this.sessionId);
      console.log('Session data:', sessionData);

      // Connect to SSE stream
      await this._connectToStream();

      this._updateStatus('active', `Session active: ${this.sessionId}`);
      this.isActive = true;

      return sessionData;

    } catch (error) {
      console.error('❌ Failed to start session:', error);
      this._updateStatus('error', `Error: ${error.message}`);
      this.onError(error);
      throw error;
    }
  }

  /**
   * Connect to SSE stream
   * @private
   */
  async _connectToStream() {
    if (!this.sessionId) {
      throw new Error('No session ID - cannot connect to stream');
    }

    const streamUrl = `${this.orchestratorUrl}/sessions/${this.sessionId}/stream`;
    console.log('📡 Connecting to SSE stream:', streamUrl);

    return new Promise((resolve, reject) => {
      this.eventSource = new EventSource(streamUrl);

      this.eventSource.onopen = () => {
        console.log('✅ SSE connection opened');
        this.isConnected = true;
        this.onConnect();
        resolve();
      };

      this.eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('📨 Received update:', data);

          // Check for errors in the data
          if (data.error) {
            console.error('Error in SSE data:', data.error);
            this.onError(new Error(data.error));
            return;
          }

          // Pass update to callback
          this.onUpdate(data);

        } catch (error) {
          console.error('Failed to parse SSE message:', error, event.data);
          this.onError(error);
        }
      };

      this.eventSource.onerror = (error) => {
        console.error('❌ SSE connection error:', error);
        this.isConnected = false;

        // Check if this is initial connection failure
        if (this.eventSource.readyState === EventSource.CONNECTING) {
          console.log('Retrying SSE connection...');
        } else if (this.eventSource.readyState === EventSource.CLOSED) {
          console.log('SSE connection closed');
          this.onDisconnect();
          reject(new Error('SSE connection failed'));
        }

        this.onError(error);
      };
    });
  }

  /**
   * Stop the current session with grace period for final updates
   * @returns {Promise<Object>} Final session state
   */
  async stopSession() {
    if (!this.sessionId) {
      console.warn('No active session to stop');
      return null;
    }

    // If already stopping, don't start another stop
    if (this.isStopping) {
      console.warn('Session is already stopping');
      return null;
    }

    this.isStopping = true;
    const sessionId = this.sessionId;

    console.log(`⏹️  Stopping session with ${this.gracePeriodSeconds}s grace period for final updates...`);

    return new Promise((resolve, reject) => {
      let countdown = this.gracePeriodSeconds;

      // Update status with countdown
      const updateCountdown = () => {
        this._updateStatus('stopping', `Stopping... waiting for final updates (${countdown}s)`);
      };

      updateCountdown();

      // Countdown timer
      const countdownInterval = setInterval(() => {
        countdown--;
        if (countdown > 0) {
          updateCountdown();
        }
      }, 1000);

      // Grace period timer - wait before actually stopping
      this.gracePeriodTimer = setTimeout(async () => {
        clearInterval(countdownInterval);
        console.log('⏰ Grace period ended, finalizing stop...');

        try {
          // Close SSE connection
          if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
            this.isConnected = false;
            console.log('SSE connection closed');
          }

          // Call orchestrator to stop session
          const response = await fetch(`${this.orchestratorUrl}/sessions/${sessionId}/stop`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({})
          });

          if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Failed to stop session: ${response.status} - ${errorText}`);
          }

          const finalState = await response.json();
          console.log('✅ Session stopped:', finalState);

          this.sessionId = null;
          this.isActive = false;
          this.isStopping = false;

          this._updateStatus('stopped', 'Session stopped');
          this.onDisconnect();

          resolve(finalState);

        } catch (error) {
          console.error('❌ Failed to stop session:', error);
          this.isStopping = false;
          this._updateStatus('error', `Error: ${error.message}`);
          this.onError(error);
          reject(error);
        }
      }, this.gracePeriodSeconds * 1000);
    });
  }

  /**
   * Cancel the grace period and stop immediately
   */
  async forceStop() {
    if (this.gracePeriodTimer) {
      clearTimeout(this.gracePeriodTimer);
      this.gracePeriodTimer = null;
    }

    this.isStopping = false;
    return this.stopSession();
  }

  /**
   * Get current session state
   * @returns {Promise<Object>} Session state
   */
  async getSessionState() {
    if (!this.sessionId) {
      throw new Error('No active session');
    }

    try {
      const response = await fetch(`${this.orchestratorUrl}/sessions/${this.sessionId}/state`);

      if (!response.ok) {
        throw new Error(`Failed to get session state: ${response.status}`);
      }

      const state = await response.json();
      return state;

    } catch (error) {
      console.error('Failed to get session state:', error);
      throw error;
    }
  }

  /**
   * Check orchestrator health
   * @returns {Promise<Object>} Health status
   */
  async checkHealth() {
    try {
      const response = await fetch(`${this.orchestratorUrl}/health`);

      if (!response.ok) {
        throw new Error(`Health check failed: ${response.status}`);
      }

      const health = await response.json();
      console.log('Orchestrator health:', health);
      return health;

    } catch (error) {
      console.error('Orchestrator health check failed:', error);
      throw error;
    }
  }

  /**
   * Update status and notify callback
   * @private
   */
  _updateStatus(state, message) {
    console.log(`Status: ${state} - ${message}`);
    this.onStatusChange(state, message);
  }

  /**
   * Clean up resources
   */
  cleanup() {
    // Clear grace period timer
    if (this.gracePeriodTimer) {
      clearTimeout(this.gracePeriodTimer);
      this.gracePeriodTimer = null;
    }

    // Close SSE connection
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }

    this.isConnected = false;
    this.isActive = false;
    this.isStopping = false;
    this.sessionId = null;
  }

  /**
   * Get current status
   */
  getStatus() {
    return {
      sessionId: this.sessionId,
      isConnected: this.isConnected,
      isActive: this.isActive,
      isStopping: this.isStopping
    };
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = SessionManager;
}
