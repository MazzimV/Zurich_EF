/**
 * Transcript Display Component
 *
 * Shows conversation transcript with speaker labels and timestamps
 */

class TranscriptDisplay {
  constructor(containerId, options = {}) {
    this.containerId = containerId;
    this.container = document.getElementById(containerId);

    // Configuration
    this.maxChunks = options.maxChunks || 100;  // Limit displayed chunks
    this.autoScroll = options.autoScroll !== false;  // Auto-scroll to latest

    // State
    this.chunks = [];

    // Initialize UI
    this._initUI();
  }

  /**
   * Initialize UI components
   */
  _initUI() {
    this.container.innerHTML = '';
    this.container.className = 'transcript-container';

    // Header - check if there's a separate header container, otherwise create in main container
    const headerContainer = document.getElementById('transcript-header-container');
    const header = document.createElement('div');
    header.className = 'transcript-header';
    header.innerHTML = `
      <h3>transcript</h3>
      <div class="transcript-controls">
        <button id="clear-transcript" class="btn-secondary">clear</button>
      </div>
    `;
    
    if (headerContainer) {
      headerContainer.appendChild(header);
    } else {
      this.container.appendChild(header);
    }

    // Transcript content area
    this.contentArea = document.createElement('div');
    this.contentArea.className = 'transcript-content';
    this.container.appendChild(this.contentArea);

    // Event listeners
    document.getElementById('clear-transcript')?.addEventListener('click', () => this.clear());
  }

  /**
   * Add a transcript chunk
   * @param {Object} chunk - Transcript chunk with text, speaker, timestamp
   */
  addChunk(chunk) {
    if (!chunk || !chunk.text) {
      console.warn('Invalid transcript chunk:', chunk);
      return;
    }

    // Add to chunks array
    this.chunks.push({
      text: chunk.text,
      speaker: chunk.speaker || 'Unknown',
      timestamp: chunk.timestamp || new Date().toISOString(),
      chunkId: chunk.chunk_id !== undefined ? chunk.chunk_id : this.chunks.length
    });

    // Limit number of displayed chunks
    if (this.chunks.length > this.maxChunks) {
      this.chunks.shift();  // Remove oldest
    }

    // Render
    this._renderChunk(this.chunks[this.chunks.length - 1]);

    // Auto-scroll if enabled
    if (this.autoScroll) {
      this._scrollToBottom();
    }
  }

  /**
   * Render a single chunk
   */
  _renderChunk(chunk) {
    const chunkElement = document.createElement('div');
    chunkElement.className = 'transcript-chunk';
    chunkElement.dataset.chunkId = chunk.chunkId;

    // Format timestamp
    const time = new Date(chunk.timestamp).toLocaleTimeString();

    chunkElement.innerHTML = `
      <div class="chunk-meta">
        <span class="chunk-speaker">${this._escapeHtml(chunk.speaker)}</span>
        <span class="chunk-time">${time}</span>
      </div>
      <div class="chunk-text">${this._escapeHtml(chunk.text)}</div>
    `;

    this.contentArea.appendChild(chunkElement);
  }

  /**
   * Render all chunks (for initial load)
   */
  renderAll() {
    this.contentArea.innerHTML = '';
    this.chunks.forEach(chunk => this._renderChunk(chunk));

    if (this.autoScroll) {
      this._scrollToBottom();
    }
  }

  /**
   * Clear all transcript chunks
   */
  clear() {
    this.chunks = [];
    this.contentArea.innerHTML = '';
    console.log('Transcript cleared');
  }

  /**
   * Load transcript from full text (for static testing)
   */
  loadFullTranscript(fullText, speaker = 'Speaker') {
    // Split into sentences for better visualization
    const sentences = fullText.match(/[^.!?]+[.!?]+/g) || [fullText];

    sentences.forEach((sentence, index) => {
      this.addChunk({
        text: sentence.trim(),
        speaker: speaker,
        timestamp: new Date(Date.now() + index * 1000).toISOString(),
        chunk_id: index
      });
    });
  }

  /**
   * Scroll to bottom of transcript
   */
  _scrollToBottom() {
    this.contentArea.scrollTop = this.contentArea.scrollHeight;
  }

  /**
   * Escape HTML to prevent XSS
   */
  _escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Get transcript stats
   */
  getStats() {
    return {
      chunkCount: this.chunks.length,
      totalCharacters: this.chunks.reduce((sum, c) => sum + c.text.length, 0)
    };
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = TranscriptDisplay;
}
