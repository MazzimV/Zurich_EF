"""
Utility functions for the speech-to-text component.

Provides helper functions for timestamps, validation, and common operations.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def generate_session_id() -> str:
    """
    Generate a unique session ID.

    Returns:
        str: Unique session identifier in format 'session-{uuid}'
    """
    return f"session-{uuid.uuid4().hex[:12]}"


def get_utc_timestamp() -> str:
    """
    Get current UTC timestamp in ISO-8601 format.

    Returns:
        str: ISO-8601 formatted timestamp (e.g., '2025-11-01T10:30:45Z')
    """
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def validate_session_id(session_id: str) -> bool:
    """
    Validate session ID format.

    Args:
        session_id: Session identifier to validate

    Returns:
        bool: True if valid, False otherwise
    """
    if not session_id or not isinstance(session_id, str):
        return False

    # Basic validation: should start with 'session-' or be a reasonable string
    if session_id.startswith('session-') or len(session_id) >= 8:
        return True

    return False


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        str: Formatted duration (e.g., '2m 30s', '45s')
    """
    if seconds < 60:
        return f"{int(seconds)}s"

    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)

    if remaining_seconds == 0:
        return f"{minutes}m"

    return f"{minutes}m {remaining_seconds}s"


def calculate_audio_size(duration_seconds: float, sample_rate: int = 16000, channels: int = 1, sample_width: int = 2) -> int:
    """
    Calculate expected audio file size in bytes.

    Args:
        duration_seconds: Audio duration in seconds
        sample_rate: Sample rate in Hz (default: 16000)
        channels: Number of audio channels (default: 1 for mono)
        sample_width: Sample width in bytes (default: 2 for 16-bit)

    Returns:
        int: Expected file size in bytes
    """
    return int(duration_seconds * sample_rate * channels * sample_width)


def truncate_text(text: str, max_length: int = 100) -> str:
    """
    Truncate text to maximum length with ellipsis.

    Args:
        text: Text to truncate
        max_length: Maximum length (default: 100)

    Returns:
        str: Truncated text with '...' if needed
    """
    if len(text) <= max_length:
        return text

    return text[:max_length - 3] + "..."


def clean_transcript_text(text: str) -> str:
    """
    Clean and normalize transcript text.

    Removes extra whitespace, normalizes line breaks, and basic cleanup.

    Args:
        text: Raw transcript text

    Returns:
        str: Cleaned transcript text
    """
    if not text:
        return ""

    # Remove extra whitespace
    text = ' '.join(text.split())

    # Strip leading/trailing whitespace
    text = text.strip()

    return text


def deduplicate_overlap(prev_text: str, new_text: str, overlap_words: int = 5) -> str:
    """
    Remove overlapping text between consecutive chunks.

    When audio chunks have overlap, the transcribed text may contain
    repeated words. This function identifies and removes the duplicate portion.

    Args:
        prev_text: Previous chunk's text
        new_text: New chunk's text
        overlap_words: Number of words to check for overlap (default: 5)

    Returns:
        str: New text with overlap removed
    """
    if not prev_text or not new_text:
        return new_text

    # Get last N words from previous text
    prev_words = prev_text.split()
    new_words = new_text.split()

    if len(prev_words) < overlap_words or len(new_words) < overlap_words:
        return new_text

    # Check for overlap by comparing last words of prev with first words of new
    last_prev_words = prev_words[-overlap_words:]

    # Try to find where the overlap starts in new_text
    for i in range(min(overlap_words, len(new_words))):
        if new_words[i:i + len(last_prev_words)] == last_prev_words:
            # Found overlap, return text after the overlap
            deduplicated = ' '.join(new_words[i + len(last_prev_words):])
            logger.debug(f"Removed overlap: '{' '.join(new_words[:i + len(last_prev_words)])}'")
            return deduplicated

    # No overlap found, return full new text
    return new_text


class AudioConfig:
    """Configuration constants for audio processing."""

    SAMPLE_RATE = 16000  # 16kHz - optimal for speech recognition
    CHANNELS = 1  # Mono audio
    SAMPLE_WIDTH = 2  # 16-bit audio (2 bytes)
    CHUNK_DURATION = 8  # seconds
    OVERLAP_DURATION = 1  # second
    SILENCE_THRESHOLD = 2.0  # seconds
    MAX_CHUNK_SIZE_MB = 25  # OpenAI Whisper API limit

    @classmethod
    def get_chunk_size_bytes(cls) -> int:
        """Get expected chunk size in bytes."""
        return calculate_audio_size(
            cls.CHUNK_DURATION,
            cls.SAMPLE_RATE,
            cls.CHANNELS,
            cls.SAMPLE_WIDTH
        )

    @classmethod
    def validate_chunk_size(cls, size_bytes: int) -> bool:
        """Validate that chunk size is within API limits."""
        max_bytes = cls.MAX_CHUNK_SIZE_MB * 1024 * 1024
        return size_bytes < max_bytes
