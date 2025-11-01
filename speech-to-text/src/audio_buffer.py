"""
Smart audio buffering with overlap handling and silence detection.

Manages audio chunks with configurable duration, overlap, and silence detection
for optimal transcription quality and UX.
"""

import io
import time
import wave
import numpy as np
from typing import Optional, Tuple
from collections import deque
import logging

from utils import AudioConfig, logger

buffer_logger = logger


class AudioBuffer:
    """
    Smart audio buffer for managing recording chunks.

    Features:
    - Time-based chunking (default: 8 seconds)
    - Overlap between chunks (default: 1 second)
    - Silence detection for adaptive chunking
    - Voice Activity Detection (VAD) support
    """

    def __init__(
        self,
        chunk_duration: float = AudioConfig.CHUNK_DURATION,
        overlap_duration: float = AudioConfig.OVERLAP_DURATION,
        sample_rate: int = AudioConfig.SAMPLE_RATE,
        channels: int = AudioConfig.CHANNELS,
        silence_threshold_seconds: float = AudioConfig.SILENCE_THRESHOLD,
        enable_vad: bool = False
    ):
        """
        Initialize the audio buffer.

        Args:
            chunk_duration: Duration of each chunk in seconds (default: 8)
            overlap_duration: Overlap between chunks in seconds (default: 1)
            sample_rate: Audio sample rate in Hz (default: 16000)
            channels: Number of audio channels (default: 1)
            silence_threshold_seconds: Seconds of silence to trigger early emit (default: 2.0)
            enable_vad: Enable Voice Activity Detection (default: False)
        """
        self.chunk_duration = chunk_duration
        self.overlap_duration = overlap_duration
        self.sample_rate = sample_rate
        self.channels = channels
        self.silence_threshold_seconds = silence_threshold_seconds
        self.enable_vad = enable_vad

        # Calculate buffer sizes in samples
        self.chunk_size_samples = int(chunk_duration * sample_rate)
        self.overlap_size_samples = int(overlap_duration * sample_rate)
        self.silence_threshold_samples = int(silence_threshold_seconds * sample_rate)

        # Audio buffer storage (using deque for efficient append/pop)
        self.buffer: deque = deque(maxlen=self.chunk_size_samples * 2)  # Allow some headroom

        # Overlap storage (keep last N samples for next chunk)
        self.overlap_buffer: deque = deque(maxlen=self.overlap_size_samples)

        # Timing
        self.chunk_start_time = time.time()
        self.last_audio_time = time.time()

        # Silence detection
        self.silence_samples_count = 0
        self.silence_threshold_energy = 0.01  # Amplitude threshold for silence

        # VAD
        self.vad = None
        if enable_vad:
            try:
                import webrtcvad
                self.vad = webrtcvad.Vad(2)  # Aggressiveness mode 2 (0-3)
                buffer_logger.info("Voice Activity Detection enabled")
            except ImportError:
                buffer_logger.warning(
                    "webrtcvad not installed. VAD disabled. "
                    "Install with: pip install webrtcvad"
                )
                self.enable_vad = False

        buffer_logger.info(
            f"AudioBuffer initialized: chunk={chunk_duration}s, "
            f"overlap={overlap_duration}s, rate={sample_rate}Hz"
        )

    def add_audio(self, audio_chunk: np.ndarray):
        """
        Add audio data to the buffer.

        Args:
            audio_chunk: Numpy array of audio samples (int16)
        """
        # Ensure audio is the correct type
        if audio_chunk.dtype != np.int16:
            audio_chunk = audio_chunk.astype(np.int16)

        # Flatten if stereo (shouldn't happen with our config, but just in case)
        if len(audio_chunk.shape) > 1:
            audio_chunk = audio_chunk.flatten()

        # Add to buffer
        self.buffer.extend(audio_chunk)

        # Update last audio time
        self.last_audio_time = time.time()

        # Check for silence
        if self._is_silence(audio_chunk):
            self.silence_samples_count += len(audio_chunk)
        else:
            self.silence_samples_count = 0  # Reset silence counter

    def should_emit(self) -> bool:
        """
        Determine if the buffer should emit a chunk for transcription.

        Returns:
            bool: True if chunk should be emitted

        Conditions for emitting:
        1. Chunk duration reached (8 seconds)
        2. Silence detected for threshold duration (2 seconds)
        3. Buffer is getting full (safety measure)
        """
        current_time = time.time()
        elapsed_time = current_time - self.chunk_start_time
        buffer_size = len(self.buffer)

        # Condition 1: Chunk duration reached
        if elapsed_time >= self.chunk_duration:
            buffer_logger.debug(f"Emitting chunk: duration reached ({elapsed_time:.1f}s)")
            return True

        # Condition 2: Silence detected after minimum duration
        if elapsed_time >= 3.0:  # At least 3 seconds of audio
            if self.silence_samples_count >= self.silence_threshold_samples:
                buffer_logger.debug(
                    f"Emitting chunk: silence detected after {elapsed_time:.1f}s"
                )
                return True

        # Condition 3: Buffer is getting full (safety measure)
        if buffer_size >= self.chunk_size_samples * 1.5:
            buffer_logger.warning(
                f"Emitting chunk: buffer full ({buffer_size} samples)"
            )
            return True

        return False

    def get_chunk(self) -> Optional[bytes]:
        """
        Get the current audio chunk as WAV bytes.

        Includes overlap from previous chunk for better transcription continuity.

        Returns:
            bytes: WAV audio data, or None if insufficient data
        """
        buffer_size = len(self.buffer)

        # Need at least some audio to transcribe
        if buffer_size < self.sample_rate:  # At least 1 second
            buffer_logger.debug(f"Insufficient audio data: {buffer_size} samples")
            return None

        # Get audio data (include overlap from previous chunk if available)
        audio_data = np.array(self.overlap_buffer, dtype=np.int16).tolist() + list(self.buffer)
        audio_array = np.array(audio_data, dtype=np.int16)

        # Store overlap for next chunk (last N samples)
        overlap_start = max(0, len(self.buffer) - self.overlap_size_samples)
        self.overlap_buffer.clear()
        self.overlap_buffer.extend(list(self.buffer)[overlap_start:])

        # Clear the main buffer
        self.buffer.clear()

        # Reset timing
        self.chunk_start_time = time.time()
        self.silence_samples_count = 0

        # Convert to WAV bytes
        wav_bytes = self._numpy_to_wav(audio_array)

        buffer_logger.info(
            f"Chunk created: {len(audio_array)} samples "
            f"({len(audio_array) / self.sample_rate:.1f}s), "
            f"{len(wav_bytes)} bytes"
        )

        return wav_bytes

    def reset(self):
        """Reset the buffer state."""
        self.buffer.clear()
        self.overlap_buffer.clear()
        self.chunk_start_time = time.time()
        self.last_audio_time = time.time()
        self.silence_samples_count = 0
        buffer_logger.info("Buffer reset")

    def get_buffer_duration(self) -> float:
        """
        Get current buffer duration in seconds.

        Returns:
            float: Duration of buffered audio in seconds
        """
        return len(self.buffer) / self.sample_rate

    def _is_silence(self, audio_chunk: np.ndarray) -> bool:
        """
        Detect if audio chunk is silence.

        Uses energy-based detection. Can be enhanced with VAD if available.

        Args:
            audio_chunk: Audio samples to analyze

        Returns:
            bool: True if chunk is silence
        """
        # Calculate RMS energy
        if len(audio_chunk) == 0:
            return True

        # Normalize to float
        audio_float = audio_chunk.astype(np.float32) / 32768.0

        # Calculate RMS energy
        rms = np.sqrt(np.mean(audio_float ** 2))

        # Simple energy-based detection
        is_silent = rms < self.silence_threshold_energy

        # TODO: Add VAD if needed
        # if self.enable_vad and self.vad:
        #     # VAD requires specific format
        #     is_speech = self._check_vad(audio_chunk)
        #     return not is_speech

        return is_silent

    def _numpy_to_wav(self, audio_array: np.ndarray) -> bytes:
        """
        Convert numpy array to WAV bytes.

        Args:
            audio_array: Audio samples as numpy array (int16)

        Returns:
            bytes: WAV file bytes
        """
        # Create an in-memory WAV file
        wav_io = io.BytesIO()

        with wave.open(wav_io, 'wb') as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(2)  # 16-bit = 2 bytes
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio_array.tobytes())

        wav_bytes = wav_io.getvalue()
        return wav_bytes

    def get_stats(self) -> dict:
        """
        Get buffer statistics.

        Returns:
            dict: Buffer statistics
        """
        return {
            'buffer_size_samples': len(self.buffer),
            'buffer_duration_seconds': self.get_buffer_duration(),
            'overlap_size_samples': len(self.overlap_buffer),
            'chunk_duration': self.chunk_duration,
            'elapsed_since_last_chunk': time.time() - self.chunk_start_time,
            'silence_detected': self.silence_samples_count >= self.silence_threshold_samples,
            'silence_duration': self.silence_samples_count / self.sample_rate
        }
