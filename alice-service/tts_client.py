"""Text-to-Speech client using ElevenLabs API."""

import logging
import base64
import os
import requests
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class TTSClient:
    """Client for converting text to speech using ElevenLabs."""

    def __init__(self):
        self.api_key = os.getenv('ELEVENLABS_API_KEY')
        self.voice_id = os.getenv('ELEVENLABS_VOICE_ID', '21m00Tcm4TlvDq8ikWAM')  # Default: Rachel
        self.model = os.getenv('ELEVENLABS_MODEL', 'eleven_monolingual_v1')
        self.base_url = "https://api.elevenlabs.io/v1"

    def text_to_speech(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Convert text to speech using ElevenLabs API.

        Args:
            text: Text to convert to speech

        Returns:
            Tuple of (audio_base64, error_message)
            - audio_base64: Base64-encoded audio data (MP3)
            - error_message: Error message if failed, None if success
        """
        if not self.api_key:
            logger.warning("ElevenLabs API key not configured, skipping TTS")
            return None, "ElevenLabs API key not configured"

        try:
            response = requests.post(
                f"{self.base_url}/text-to-speech/{self.voice_id}",
                headers={
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json",
                    "xi-api-key": self.api_key
                },
                json={
                    "text": text,
                    "model_id": self.model,
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75
                    }
                },
                timeout=30.0
            )

            if response.status_code == 200:
                # Encode audio as base64
                audio_bytes = response.content
                audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                logger.info(f"Successfully generated TTS audio ({len(audio_bytes)} bytes)")
                return audio_base64, None
            else:
                error_msg = f"ElevenLabs API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return None, error_msg

        except requests.Timeout:
            error_msg = "ElevenLabs API timeout"
            logger.error(error_msg)
            return None, error_msg
        except Exception as e:
            error_msg = f"Failed to generate TTS: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return None, error_msg
