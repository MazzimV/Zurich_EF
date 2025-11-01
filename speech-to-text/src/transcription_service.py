"""
Transcription service for converting audio to text using OpenAI GPT-4o Transcribe API.

Handles API communication, error handling, retries, response processing, and speaker diarization.
"""

import os
import io
import time
import logging
from typing import Optional, Dict, Any
from openai import OpenAI
from openai import OpenAIError, APIError, RateLimitError, APIConnectionError

from utils import clean_transcript_text, logger

# Get logger from utils
transcription_logger = logger


class TranscriptionError(Exception):
    """Custom exception for transcription errors."""
    pass


class TranscriptionService:
    """
    Service for transcribing audio using OpenAI GPT-4o Transcribe API.

    Handles:
    - API authentication
    - Audio transcription with retry logic
    - Speaker diarization (identifies who's speaking)
    - Error handling and logging
    - Response validation
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-transcribe-diarize",
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize the transcription service.

        Args:
            api_key: OpenAI API key (if None, reads from OPENAI_API_KEY env var)
            model: Transcription model to use (default: 'gpt-4o-transcribe-diarize')
            max_retries: Maximum number of retry attempts (default: 3)
            retry_delay: Initial delay between retries in seconds (default: 1.0)
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key not provided. Set OPENAI_API_KEY environment variable.")

        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Statistics tracking
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_retries': 0,
            'total_audio_seconds': 0.0
        }

        transcription_logger.info(f"TranscriptionService initialized with model: {self.model}")

    def transcribe_audio(
        self,
        audio_data: bytes,
        filename: str = "audio.wav",
        language: Optional[str] = None,
        prompt: Optional[str] = None,
        include_speaker_labels: bool = True
    ) -> str:
        """
        Transcribe audio data to text using OpenAI GPT-4o Transcribe API with speaker diarization.

        Implements retry logic with exponential backoff for reliability.

        Args:
            audio_data: Audio file bytes (WAV format recommended)
            filename: Filename to send to API (default: 'audio.wav')
            language: Optional ISO-639-1 language code (e.g., 'en', 'es')
            prompt: Optional prompt to guide the model's style
            include_speaker_labels: Whether to include speaker labels in output (default: True)

        Returns:
            str: Transcribed text with speaker labels (e.g., "A: Hello\nB: Hi there")

        Raises:
            TranscriptionError: If transcription fails after all retries
        """
        self.stats['total_requests'] += 1

        for attempt in range(self.max_retries):
            try:
                transcription_logger.debug(
                    f"Transcription attempt {attempt + 1}/{self.max_retries} "
                    f"(size: {len(audio_data)} bytes)"
                )

                # Create file-like object from bytes
                audio_file = io.BytesIO(audio_data)
                audio_file.name = filename

                # Call OpenAI GPT-4o Transcribe API with diarization
                start_time = time.time()

                response = self.client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file,
                    language=language,
                    prompt=prompt,
                    response_format="diarized_json"
                )

                elapsed_time = time.time() - start_time

                # Extract text from diarized response
                # Response contains segments with speaker, text, start, end
                if hasattr(response, 'segments') and response.segments:
                    # Process segments with speaker labels
                    segments = []
                    current_speaker = None

                    for segment in response.segments:
                        speaker = getattr(segment, 'speaker', 'Unknown')
                        segment_text = getattr(segment, 'text', '').strip()

                        if not segment_text:
                            continue

                        # Include speaker label if enabled and speaker changed
                        if include_speaker_labels:
                            if speaker != current_speaker:
                                segments.append(f"{speaker}: {segment_text}")
                                current_speaker = speaker
                            else:
                                # Same speaker continuing, just add text
                                segments.append(segment_text)
                        else:
                            segments.append(segment_text)

                    text = " ".join(segments)
                elif isinstance(response, str):
                    # Fallback for plain text response
                    text = response
                else:
                    # Fallback for other response types
                    text = response.text if hasattr(response, 'text') else str(response)

                # Clean and validate the transcript
                text = clean_transcript_text(text)

                if not text:
                    transcription_logger.warning("Received empty transcription from API")
                    # Don't treat empty response as error, might be silence
                    self.stats['successful_requests'] += 1
                    return ""

                # Success!
                self.stats['successful_requests'] += 1
                transcription_logger.info(
                    f"Transcription successful in {elapsed_time:.2f}s: "
                    f"'{text[:50]}{'...' if len(text) > 50 else ''}'"
                )

                return text

            except RateLimitError as e:
                # Rate limit hit, wait longer before retry
                self.stats['total_retries'] += 1
                wait_time = self.retry_delay * (2 ** attempt) * 2  # Double the backoff for rate limits
                transcription_logger.warning(
                    f"Rate limit error on attempt {attempt + 1}: {str(e)}. "
                    f"Waiting {wait_time}s before retry..."
                )

                if attempt < self.max_retries - 1:
                    time.sleep(wait_time)
                else:
                    self.stats['failed_requests'] += 1
                    raise TranscriptionError(f"Rate limit exceeded after {self.max_retries} attempts") from e

            except APIConnectionError as e:
                # Network error, retry with backoff
                self.stats['total_retries'] += 1
                wait_time = self.retry_delay * (2 ** attempt)
                transcription_logger.warning(
                    f"API connection error on attempt {attempt + 1}: {str(e)}. "
                    f"Waiting {wait_time}s before retry..."
                )

                if attempt < self.max_retries - 1:
                    time.sleep(wait_time)
                else:
                    self.stats['failed_requests'] += 1
                    raise TranscriptionError(f"Connection failed after {self.max_retries} attempts") from e

            except APIError as e:
                # API error, retry with backoff
                self.stats['total_retries'] += 1
                wait_time = self.retry_delay * (2 ** attempt)
                transcription_logger.error(
                    f"API error on attempt {attempt + 1}: {str(e)}. "
                    f"Waiting {wait_time}s before retry..."
                )

                if attempt < self.max_retries - 1:
                    time.sleep(wait_time)
                else:
                    self.stats['failed_requests'] += 1
                    raise TranscriptionError(f"API error after {self.max_retries} attempts: {str(e)}") from e

            except OpenAIError as e:
                # Generic OpenAI error
                self.stats['total_retries'] += 1
                transcription_logger.error(f"OpenAI error on attempt {attempt + 1}: {str(e)}")

                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))
                else:
                    self.stats['failed_requests'] += 1
                    raise TranscriptionError(f"OpenAI error after {self.max_retries} attempts: {str(e)}") from e

            except Exception as e:
                # Unexpected error
                transcription_logger.error(f"Unexpected error during transcription: {str(e)}", exc_info=True)
                self.stats['failed_requests'] += 1
                raise TranscriptionError(f"Unexpected error: {str(e)}") from e

        # Should never reach here, but just in case
        self.stats['failed_requests'] += 1
        raise TranscriptionError(f"Transcription failed after {self.max_retries} attempts")

    def transcribe_file(self, filepath: str, **kwargs) -> str:
        """
        Transcribe an audio file from disk.

        Convenience method for transcribing files.

        Args:
            filepath: Path to audio file
            **kwargs: Additional arguments passed to transcribe_audio()

        Returns:
            str: Transcribed text

        Raises:
            FileNotFoundError: If file doesn't exist
            TranscriptionError: If transcription fails
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Audio file not found: {filepath}")

        transcription_logger.info(f"Transcribing file: {filepath}")

        with open(filepath, 'rb') as f:
            audio_data = f.read()

        filename = os.path.basename(filepath)
        return self.transcribe_audio(audio_data, filename=filename, **kwargs)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get transcription service statistics.

        Returns:
            dict: Statistics including request counts, retries, etc.
        """
        success_rate = 0.0
        if self.stats['total_requests'] > 0:
            success_rate = (self.stats['successful_requests'] / self.stats['total_requests']) * 100

        return {
            **self.stats,
            'success_rate': f"{success_rate:.1f}%",
            'avg_retries_per_request': (
                self.stats['total_retries'] / max(self.stats['total_requests'], 1)
            )
        }

    def reset_stats(self):
        """Reset statistics counters."""
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_retries': 0,
            'total_audio_seconds': 0.0
        }
        transcription_logger.info("Statistics reset")


# Singleton instance for convenience
_default_service: Optional[TranscriptionService] = None


def get_transcription_service() -> TranscriptionService:
    """
    Get the default transcription service instance (singleton).

    Returns:
        TranscriptionService: The default service instance
    """
    global _default_service

    if _default_service is None:
        _default_service = TranscriptionService()

    return _default_service
