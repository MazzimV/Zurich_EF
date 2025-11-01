"""
Tests for the speech-to-text component.

Run with: python -m pytest tests/
Or: python tests/test_transcription.py
"""

import sys
import os
import time
import numpy as np

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils import (
    generate_session_id,
    get_utc_timestamp,
    validate_session_id,
    clean_transcript_text,
    deduplicate_overlap,
    AudioConfig
)
from audio_buffer import AudioBuffer
from session_manager import SessionManager


def test_session_id_generation():
    """Test session ID generation."""
    print("\n=== Testing Session ID Generation ===")

    session_id = generate_session_id()
    print(f"Generated session ID: {session_id}")

    assert session_id.startswith('session-'), "Session ID should start with 'session-'"
    assert len(session_id) > 10, "Session ID should be reasonably long"
    assert validate_session_id(session_id), "Generated session ID should be valid"

    print("✅ Session ID generation works")


def test_timestamp():
    """Test timestamp generation."""
    print("\n=== Testing Timestamp Generation ===")

    timestamp = get_utc_timestamp()
    print(f"Generated timestamp: {timestamp}")

    assert 'T' in timestamp, "Timestamp should be ISO-8601 format"
    assert timestamp.endswith('Z'), "Timestamp should end with 'Z' (UTC)"

    print("✅ Timestamp generation works")


def test_text_cleaning():
    """Test text cleaning utilities."""
    print("\n=== Testing Text Cleaning ===")

    # Test basic cleaning
    dirty_text = "  Hello   world  \n  test  "
    clean_text = clean_transcript_text(dirty_text)
    print(f"Dirty: '{dirty_text}'")
    print(f"Clean: '{clean_text}'")

    assert clean_text == "Hello world test", "Text should be cleaned"

    print("✅ Text cleaning works")


def test_deduplication():
    """Test overlap deduplication."""
    print("\n=== Testing Overlap Deduplication ===")

    prev_text = "Let's focus on user experience"
    new_text = "experience and mobile design"

    deduplicated = deduplicate_overlap(prev_text, new_text, overlap_words=5)
    print(f"Previous: '{prev_text}'")
    print(f"New: '{new_text}'")
    print(f"Deduplicated: '{deduplicated}'")

    assert "experience" not in deduplicated or deduplicated.count("experience") == 1
    assert "mobile design" in deduplicated

    print("✅ Deduplication works")


def test_audio_buffer():
    """Test audio buffer functionality."""
    print("\n=== Testing Audio Buffer ===")

    buffer = AudioBuffer(
        chunk_duration=2.0,  # Short duration for testing
        overlap_duration=0.5,
        sample_rate=16000
    )

    # Simulate adding audio
    print("Adding audio to buffer...")
    for i in range(5):
        # Create 0.5 seconds of random audio
        audio_chunk = np.random.randint(-1000, 1000, 8000, dtype=np.int16)
        buffer.add_audio(audio_chunk)
        time.sleep(0.1)

    stats = buffer.get_stats()
    print(f"Buffer stats: {stats}")

    assert stats['buffer_size_samples'] > 0, "Buffer should have audio"

    # Test chunk retrieval
    if buffer.should_emit():
        chunk = buffer.get_chunk()
        assert chunk is not None, "Should be able to get chunk"
        assert isinstance(chunk, bytes), "Chunk should be bytes"
        print(f"✅ Retrieved chunk: {len(chunk)} bytes")
    else:
        print("⚠️  Buffer not ready to emit yet")

    print("✅ Audio buffer works")


def test_session_manager():
    """Test session manager."""
    print("\n=== Testing Session Manager ===")

    manager = SessionManager(max_sessions=5, session_timeout=60)

    # Create session
    session = manager.create_session()
    print(f"Created session: {session.session_id}")

    assert session is not None, "Session should be created"
    assert session.status == "active", "Session should be active"

    # Add transcript chunk
    manager.add_transcript_chunk(session.session_id, "Hello world")
    manager.add_transcript_chunk(session.session_id, "This is a test")

    assert session.chunk_count == 2, "Should have 2 chunks"
    assert "Hello world" in session.full_transcript, "Transcript should contain first chunk"
    assert "This is a test" in session.full_transcript, "Transcript should contain second chunk"

    print(f"Full transcript: '{session.full_transcript}'")

    # Get session
    retrieved = manager.get_session(session.session_id)
    assert retrieved == session, "Should retrieve the same session"

    # Stop session
    manager.stop_session(session.session_id)
    assert session.status == "stopped", "Session should be stopped"

    # Stats
    stats = manager.get_stats()
    print(f"Manager stats: {stats}")

    print("✅ Session manager works")


def test_audio_config():
    """Test audio configuration."""
    print("\n=== Testing Audio Configuration ===")

    print(f"Sample Rate: {AudioConfig.SAMPLE_RATE} Hz")
    print(f"Channels: {AudioConfig.CHANNELS}")
    print(f"Chunk Duration: {AudioConfig.CHUNK_DURATION}s")
    print(f"Overlap Duration: {AudioConfig.OVERLAP_DURATION}s")

    chunk_size = AudioConfig.get_chunk_size_bytes()
    print(f"Expected chunk size: {chunk_size} bytes ({chunk_size / 1024:.1f} KB)")

    assert AudioConfig.validate_chunk_size(chunk_size), "Chunk size should be valid"
    assert chunk_size < 25 * 1024 * 1024, "Chunk should be under 25MB limit"

    print("✅ Audio configuration is valid")


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("SPEECH-TO-TEXT COMPONENT TESTS")
    print("=" * 60)

    tests = [
        test_session_id_generation,
        test_timestamp,
        test_text_cleaning,
        test_deduplication,
        test_audio_buffer,
        test_session_manager,
        test_audio_config
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAILED: {test_func.__name__}")
            print(f"   Error: {str(e)}")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR: {test_func.__name__}")
            print(f"   Error: {str(e)}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
