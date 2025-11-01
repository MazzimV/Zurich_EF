"""
Session management for tracking recording sessions.

Manages session state, transcript accumulation, and session lifecycle.
"""

import time
import threading
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from utils import generate_session_id, get_utc_timestamp, validate_session_id, deduplicate_overlap, logger

session_logger = logger


@dataclass
class TranscriptChunk:
    """Represents a single transcript chunk."""
    chunk_id: int
    text: str
    timestamp: str
    confidence: Optional[float] = None
    duration_ms: Optional[int] = None


@dataclass
class Session:
    """Represents a recording session."""
    session_id: str
    started_at: str
    status: str = "active"  # active, paused, stopped, error
    full_transcript: str = ""
    chunks: List[TranscriptChunk] = field(default_factory=list)
    chunk_count: int = 0
    total_duration: float = 0.0
    last_chunk_text: str = ""  # For deduplication
    paused_at: Optional[str] = None
    resumed_at: Optional[str] = None
    pause_count: int = 0
    total_paused_duration: float = 0.0
    metadata: Dict = field(default_factory=dict)

    def add_chunk(self, text: str, confidence: Optional[float] = None):
        """
        Add a new transcript chunk to the session.

        Args:
            text: Transcribed text
            confidence: Optional confidence score
        """
        # Deduplicate overlap with previous chunk
        if self.last_chunk_text:
            text = deduplicate_overlap(self.last_chunk_text, text)

        # Skip if text is empty after deduplication
        if not text or text.strip() == "":
            session_logger.debug(f"Skipping empty chunk for session {self.session_id}")
            return

        # Create chunk
        chunk = TranscriptChunk(
            chunk_id=self.chunk_count,
            text=text,
            timestamp=get_utc_timestamp(),
            confidence=confidence
        )

        # Add to session
        self.chunks.append(chunk)
        self.full_transcript += " " + text if self.full_transcript else text
        self.last_chunk_text = text
        self.chunk_count += 1

        session_logger.info(
            f"Session {self.session_id}: Added chunk #{chunk.chunk_id} "
            f"({len(text)} chars)"
        )

    def get_latest_chunk(self) -> Optional[TranscriptChunk]:
        """Get the most recent transcript chunk."""
        if not self.chunks:
            return None
        return self.chunks[-1]

    def get_duration(self) -> float:
        """Get session duration in seconds."""
        started = datetime.fromisoformat(self.started_at.replace('Z', '+00:00'))
        now = datetime.now(started.tzinfo)
        return (now - started).total_seconds()

    def to_dict(self) -> dict:
        """Convert session to dictionary for JSON serialization."""
        return {
            'session_id': self.session_id,
            'started_at': self.started_at,
            'status': self.status,
            'full_transcript': self.full_transcript,
            'chunk_count': self.chunk_count,
            'total_duration': self.get_duration(),
            'paused_at': self.paused_at,
            'resumed_at': self.resumed_at,
            'pause_count': self.pause_count,
            'total_paused_duration': self.total_paused_duration,
            'metadata': self.metadata
        }

    def get_chunks_dict(self) -> List[dict]:
        """Get all chunks as dictionaries."""
        return [
            {
                'chunk_id': chunk.chunk_id,
                'text': chunk.text,
                'timestamp': chunk.timestamp,
                'confidence': chunk.confidence,
                'duration_ms': chunk.duration_ms
            }
            for chunk in self.chunks
        ]


class SessionManager:
    """
    Manage multiple recording sessions.

    Thread-safe session management with automatic cleanup.
    """

    def __init__(self, max_sessions: int = 10, session_timeout: float = 3600):
        """
        Initialize the session manager.

        Args:
            max_sessions: Maximum number of concurrent sessions (default: 10)
            session_timeout: Session timeout in seconds (default: 3600 = 1 hour)
        """
        self.sessions: Dict[str, Session] = {}
        self.max_sessions = max_sessions
        self.session_timeout = session_timeout
        self._lock = threading.Lock()

        # Cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()

        session_logger.info(
            f"SessionManager initialized: max_sessions={max_sessions}, "
            f"timeout={session_timeout}s"
        )

    def create_session(self, session_id: Optional[str] = None) -> Session:
        """
        Create a new recording session.

        Args:
            session_id: Optional custom session ID (auto-generated if None)

        Returns:
            Session: The created session

        Raises:
            ValueError: If session already exists or max sessions reached
        """
        with self._lock:
            # Check max sessions limit
            if len(self.sessions) >= self.max_sessions:
                raise ValueError(f"Maximum number of sessions ({self.max_sessions}) reached")

            # Generate session ID if not provided
            if session_id is None:
                session_id = generate_session_id()
            elif not validate_session_id(session_id):
                raise ValueError(f"Invalid session ID: {session_id}")

            # Check if session already exists
            if session_id in self.sessions:
                raise ValueError(f"Session {session_id} already exists")

            # Create session
            session = Session(
                session_id=session_id,
                started_at=get_utc_timestamp()
            )

            self.sessions[session_id] = session
            session_logger.info(f"Created session: {session_id}")

            return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get a session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session: The session, or None if not found
        """
        with self._lock:
            return self.sessions.get(session_id)

    def stop_session(self, session_id: str) -> Optional[Session]:
        """
        Stop a session.

        Args:
            session_id: Session identifier

        Returns:
            Session: The stopped session, or None if not found
        """
        with self._lock:
            session = self.sessions.get(session_id)
            if session:
                session.status = "stopped"
                session.total_duration = session.get_duration()
                session_logger.info(
                    f"Stopped session {session_id}: "
                    f"{session.chunk_count} chunks, "
                    f"{session.total_duration:.1f}s"
                )
            return session

    def pause_session(self, session_id: str) -> Optional[Session]:
        """
        Pause a session - stops audio capture but keeps state.

        Args:
            session_id: Session identifier

        Returns:
            Session: The paused session, or None if not found

        Raises:
            ValueError: If session is not in 'active' state
        """
        with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return None

            if session.status != "active":
                raise ValueError(f"Can only pause active sessions (current: {session.status})")

            # Calculate paused duration from last resume (or start)
            if session.resumed_at:
                last_active = datetime.fromisoformat(session.resumed_at.replace('Z', '+00:00'))
            else:
                last_active = datetime.fromisoformat(session.started_at.replace('Z', '+00:00'))

            now = datetime.now(last_active.tzinfo)
            active_duration = (now - last_active).total_seconds()

            # Update session state
            session.status = "paused"
            session.paused_at = get_utc_timestamp()
            session.pause_count += 1

            session_logger.info(
                f"Paused session {session_id} "
                f"(pause #{session.pause_count}, "
                f"was active for {active_duration:.1f}s)"
            )

            return session

    def resume_session(self, session_id: str) -> Optional[Session]:
        """
        Resume a paused session - continues from current state.

        Args:
            session_id: Session identifier

        Returns:
            Session: The resumed session, or None if not found

        Raises:
            ValueError: If session is not in 'paused' state
        """
        with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return None

            if session.status != "paused":
                raise ValueError(f"Can only resume paused sessions (current: {session.status})")

            # Calculate paused duration
            if session.paused_at:
                paused_start = datetime.fromisoformat(session.paused_at.replace('Z', '+00:00'))
                now = datetime.now(paused_start.tzinfo)
                paused_duration = (now - paused_start).total_seconds()
                session.total_paused_duration += paused_duration
            else:
                paused_duration = 0.0

            # Update session state
            session.status = "active"
            session.resumed_at = get_utc_timestamp()

            session_logger.info(
                f"Resumed session {session_id} "
                f"(was paused for {paused_duration:.1f}s, "
                f"total paused: {session.total_paused_duration:.1f}s)"
            )

            return session

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session identifier

        Returns:
            bool: True if session was deleted, False if not found
        """
        with self._lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                session_logger.info(f"Deleted session: {session_id}")
                return True
            return False

    def add_transcript_chunk(
        self,
        session_id: str,
        text: str,
        confidence: Optional[float] = None
    ) -> bool:
        """
        Add a transcript chunk to a session.

        Args:
            session_id: Session identifier
            text: Transcribed text
            confidence: Optional confidence score

        Returns:
            bool: True if added successfully, False if session not found
        """
        with self._lock:
            session = self.sessions.get(session_id)
            if session:
                session.add_chunk(text, confidence)
                return True
            return False

    def get_all_sessions(self) -> List[Session]:
        """
        Get all sessions.

        Returns:
            List[Session]: List of all sessions
        """
        with self._lock:
            return list(self.sessions.values())

    def get_active_sessions(self) -> List[Session]:
        """
        Get all active sessions.

        Returns:
            List[Session]: List of active sessions
        """
        with self._lock:
            return [s for s in self.sessions.values() if s.status == "active"]

    def get_stats(self) -> dict:
        """
        Get session manager statistics.

        Returns:
            dict: Statistics about sessions
        """
        with self._lock:
            active_count = len([s for s in self.sessions.values() if s.status == "active"])
            total_chunks = sum(s.chunk_count for s in self.sessions.values())

            return {
                'total_sessions': len(self.sessions),
                'active_sessions': active_count,
                'total_chunks_processed': total_chunks,
                'max_sessions': self.max_sessions
            }

    def _cleanup_loop(self):
        """Background thread for cleaning up old sessions."""
        while True:
            try:
                time.sleep(60)  # Check every minute
                self._cleanup_old_sessions()
            except Exception as e:
                session_logger.error(f"Error in cleanup loop: {str(e)}", exc_info=True)

    def _cleanup_old_sessions(self):
        """Remove old stopped sessions that have timed out."""
        with self._lock:
            current_time = time.time()
            sessions_to_delete = []

            for session_id, session in self.sessions.items():
                if session.status != "active":
                    session_age = session.get_duration()
                    if session_age > self.session_timeout:
                        sessions_to_delete.append(session_id)

            for session_id in sessions_to_delete:
                del self.sessions[session_id]
                session_logger.info(f"Cleaned up old session: {session_id}")

            if sessions_to_delete:
                session_logger.info(f"Cleaned up {len(sessions_to_delete)} old sessions")


# Singleton instance
_default_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """
    Get the default session manager instance (singleton).

    Returns:
        SessionManager: The default manager instance
    """
    global _default_manager

    if _default_manager is None:
        _default_manager = SessionManager()

    return _default_manager
