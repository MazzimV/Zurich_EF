"""
Audio capture from microphone using sounddevice.

Handles real-time audio recording with configurable settings.
"""

import time
import threading
import queue
import numpy as np
import sounddevice as sd
from typing import Optional, Callable
import logging

from utils import AudioConfig, logger

capture_logger = logger


class AudioCaptureError(Exception):
    """Custom exception for audio capture errors."""
    pass


class AudioCapture:
    """
    Capture audio from the default microphone.

    Uses sounddevice for cross-platform audio input.
    Runs capture in a separate thread for non-blocking operation.
    """

    def __init__(
        self,
        sample_rate: int = AudioConfig.SAMPLE_RATE,
        channels: int = AudioConfig.CHANNELS,
        block_duration: float = 0.1,  # 100ms blocks
        callback: Optional[Callable[[np.ndarray], None]] = None
    ):
        """
        Initialize audio capture.

        Args:
            sample_rate: Sample rate in Hz (default: 16000)
            channels: Number of channels (default: 1 for mono)
            block_duration: Duration of each audio block in seconds (default: 0.1)
            callback: Optional callback function called with each audio block
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.block_duration = block_duration
        self.blocksize = int(block_duration * sample_rate)
        self.callback = callback

        # Audio queue for thread-safe communication
        self.audio_queue: queue.Queue = queue.Queue()

        # State
        self.is_recording = False
        self.stream: Optional[sd.InputStream] = None
        self.capture_thread: Optional[threading.Thread] = None

        # Statistics
        self.total_blocks_captured = 0
        self.total_samples_captured = 0
        self.start_time: Optional[float] = None

        capture_logger.info(
            f"AudioCapture initialized: rate={sample_rate}Hz, "
            f"channels={channels}, block={block_duration}s"
        )

    def start(self):
        """
        Start capturing audio from the microphone.

        Raises:
            AudioCaptureError: If capture fails to start
        """
        if self.is_recording:
            capture_logger.warning("Audio capture already running")
            return

        try:
            # List available devices (for debugging)
            capture_logger.debug("Available audio devices:")
            devices = sd.query_devices()
            for i, device in enumerate(devices):
                if device['max_input_channels'] > 0:
                    capture_logger.debug(
                        f"  [{i}] {device['name']} "
                        f"(channels: {device['max_input_channels']})"
                    )

            # Start the audio stream
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=np.int16,
                blocksize=self.blocksize,
                callback=self._audio_callback
            )

            self.stream.start()
            self.is_recording = True
            self.start_time = time.time()
            self.total_blocks_captured = 0
            self.total_samples_captured = 0

            capture_logger.info("Audio capture started")

        except Exception as e:
            capture_logger.error(f"Failed to start audio capture: {str(e)}", exc_info=True)
            raise AudioCaptureError(f"Failed to start capture: {str(e)}") from e

    def stop(self):
        """Stop capturing audio."""
        if not self.is_recording:
            capture_logger.warning("Audio capture not running")
            return

        try:
            self.is_recording = False

            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None

            # Calculate stats
            if self.start_time:
                duration = time.time() - self.start_time
                capture_logger.info(
                    f"Audio capture stopped. "
                    f"Duration: {duration:.1f}s, "
                    f"Blocks: {self.total_blocks_captured}, "
                    f"Samples: {self.total_samples_captured}"
                )

        except Exception as e:
            capture_logger.error(f"Error stopping audio capture: {str(e)}", exc_info=True)

    def read(self, timeout: Optional[float] = None) -> Optional[np.ndarray]:
        """
        Read an audio block from the queue.

        Args:
            timeout: Maximum time to wait for audio in seconds (None = blocking)

        Returns:
            np.ndarray: Audio samples (int16), or None if timeout
        """
        try:
            audio_block = self.audio_queue.get(timeout=timeout)
            return audio_block
        except queue.Empty:
            return None

    def _audio_callback(self, indata, frames, time_info, status):
        """
        Callback function called by sounddevice for each audio block.

        Args:
            indata: Input audio data
            frames: Number of frames
            time_info: Time information
            status: Status flags
        """
        if status:
            capture_logger.warning(f"Audio callback status: {status}")

        # Convert to int16 if needed
        if indata.dtype != np.int16:
            audio_block = (indata * 32767).astype(np.int16)
        else:
            audio_block = indata.copy()

        # Flatten if stereo
        if self.channels == 1 and len(audio_block.shape) > 1:
            audio_block = audio_block.flatten()

        # Update statistics
        self.total_blocks_captured += 1
        self.total_samples_captured += len(audio_block)

        # Put in queue
        try:
            self.audio_queue.put_nowait(audio_block)
        except queue.Full:
            capture_logger.warning("Audio queue full, dropping block")

        # Call user callback if provided (only if still recording)
        if self.callback and self.is_recording:
            try:
                self.callback(audio_block)
            except Exception as e:
                capture_logger.error(f"Error in user callback: {str(e)}", exc_info=True)

    def get_duration(self) -> float:
        """
        Get total duration of captured audio in seconds.

        Returns:
            float: Duration in seconds
        """
        if self.total_samples_captured == 0:
            return 0.0

        return self.total_samples_captured / self.sample_rate

    def get_stats(self) -> dict:
        """
        Get capture statistics.

        Returns:
            dict: Statistics about the capture
        """
        duration = self.get_duration()
        elapsed = (time.time() - self.start_time) if self.start_time else 0

        return {
            'is_recording': self.is_recording,
            'total_blocks': self.total_blocks_captured,
            'total_samples': self.total_samples_captured,
            'audio_duration_seconds': duration,
            'elapsed_time_seconds': elapsed,
            'queue_size': self.audio_queue.qsize(),
            'sample_rate': self.sample_rate,
            'channels': self.channels
        }

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


def list_audio_devices():
    """
    List all available audio input devices.

    Returns:
        list: List of input device information
    """
    devices = sd.query_devices()
    input_devices = []

    print("\nAvailable Audio Input Devices:")
    print("-" * 60)

    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            input_devices.append({
                'index': i,
                'name': device['name'],
                'channels': device['max_input_channels'],
                'sample_rate': device['default_samplerate']
            })
            print(f"[{i}] {device['name']}")
            print(f"    Channels: {device['max_input_channels']}, "
                  f"Sample Rate: {device['default_samplerate']} Hz")

    print("-" * 60)

    return input_devices


def test_microphone(duration: float = 5.0):
    """
    Test microphone by recording for a specified duration.

    Args:
        duration: Recording duration in seconds
    """
    print(f"\nTesting microphone for {duration} seconds...")
    print("Speak into your microphone!")

    captured_blocks = []

    def callback(audio_block):
        captured_blocks.append(audio_block)

    capture = AudioCapture(callback=callback)

    try:
        capture.start()
        time.sleep(duration)
        capture.stop()

        stats = capture.get_stats()
        print(f"\nCapture completed:")
        print(f"  Blocks captured: {stats['total_blocks']}")
        print(f"  Total samples: {stats['total_samples']}")
        print(f"  Duration: {stats['audio_duration_seconds']:.2f}s")

        # Calculate audio level
        if captured_blocks:
            all_audio = np.concatenate(captured_blocks)
            rms = np.sqrt(np.mean((all_audio.astype(np.float32) / 32768.0) ** 2))
            print(f"  Average RMS level: {rms:.4f}")

            if rms < 0.01:
                print("  ⚠️  Audio level is very low. Check your microphone!")
            else:
                print("  ✅ Microphone is working!")

    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    # Test the audio capture
    list_audio_devices()
    test_microphone(duration=5.0)
