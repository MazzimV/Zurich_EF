"""
Session Orchestrator - Core Logic

Manages sessions that bridge speech-to-text and graph-generation components.
Handles state, coordinates API calls, and streams unified output.
"""

import logging
import time
import uuid
import os
import json
from typing import Dict, Optional, Any
from datetime import datetime
import threading
import queue

logger = logging.getLogger(__name__)


class SessionOrchestrator:
    """
    Orchestrates sessions between speech-to-text and graph-generation services.

    Responsibilities:
    - Manage session lifecycle (create, active, stopped)
    - Store session state (graph, transcript history)
    - Coordinate between STT and graph-gen services
    - Provide unified data stream
    """

    def __init__(self, max_sessions: int = 10, save_directory: str = "./sessions"):
        """
        Initialize the orchestrator.

        Args:
            max_sessions: Maximum number of concurrent sessions
            save_directory: Directory to save session files (default: ./sessions)
        """
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.max_sessions = max_sessions
        self.lock = threading.Lock()
        self.save_directory = save_directory

        # Create save directory if it doesn't exist
        os.makedirs(save_directory, exist_ok=True)

        logger.info(f"SessionOrchestrator initialized: max_sessions={max_sessions}, save_dir={save_directory}")

    def create_session(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new orchestrator session.

        Args:
            session_id: Optional custom session ID, auto-generated if not provided

        Returns:
            dict: Session info with session_id, status, created_at

        Raises:
            ValueError: If max sessions reached
        """
        with self.lock:
            # Check session limit
            if len(self.sessions) >= self.max_sessions:
                raise ValueError(f"Maximum number of sessions ({self.max_sessions}) reached")

            # Generate session ID if not provided
            if not session_id:
                session_id = f"session-{uuid.uuid4().hex[:12]}"

            # Check if session already exists
            if session_id in self.sessions:
                raise ValueError(f"Session {session_id} already exists")

            # Create session state
            now = datetime.utcnow().isoformat() + 'Z'
            self.sessions[session_id] = {
                'session_id': session_id,
                'status': 'created',  # created, active, paused, stopped
                'created_at': now,
                'started_at': None,
                'stopped_at': None,
                'paused_at': None,
                'resumed_at': None,
                'pause_count': 0,
                'total_paused_duration': 0.0,
                'graph': None,  # Current graph state
                'graph_version': 0,
                'transcript_chunks': [],  # List of all transcript chunks
                'full_transcript': '',  # Concatenated transcript (all text so far)
                'transcript_for_current_graph': '',  # Snapshot of transcript when graph was last updated
                'chunk_count': 0,
                'stt_session_id': None,  # Speech-to-text session ID
                'metadata': {
                    'total_graph_updates': 0,
                    'last_update_at': None,
                    'errors': []
                }
            }

            logger.info(f"Created session: {session_id}")

            return {
                'session_id': session_id,
                'status': 'created',
                'created_at': now
            }

    def start_session(self, session_id: str, stt_session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Start a session (mark as active).

        Args:
            session_id: Session ID to start
            stt_session_id: Optional STT session ID to link

        Returns:
            dict: Updated session info

        Raises:
            ValueError: If session doesn't exist
        """
        with self.lock:
            if session_id not in self.sessions:
                raise ValueError(f"Session {session_id} not found")

            session = self.sessions[session_id]

            if session['status'] == 'stopped':
                raise ValueError(f"Session {session_id} is already stopped")

            now = datetime.utcnow().isoformat() + 'Z'
            session['status'] = 'active'
            session['started_at'] = now

            if stt_session_id:
                session['stt_session_id'] = stt_session_id

            logger.info(f"Started session: {session_id}")

            return {
                'session_id': session_id,
                'status': 'active',
                'started_at': now,
                'stt_session_id': stt_session_id
            }

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session state.

        Args:
            session_id: Session ID

        Returns:
            dict: Session state or None if not found
        """
        with self.lock:
            return self.sessions.get(session_id)

    def update_graph(
        self,
        session_id: str,
        new_graph: Dict[str, Any],
        chunk_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update the graph for a session.

        Args:
            session_id: Session ID
            new_graph: New graph data from graph-generation
            chunk_info: Optional info about the transcript chunk that triggered this update

        Returns:
            dict: Updated session state

        Raises:
            ValueError: If session doesn't exist
        """
        with self.lock:
            if session_id not in self.sessions:
                raise ValueError(f"Session {session_id} not found")

            session = self.sessions[session_id]

            # Update graph
            session['graph'] = new_graph
            session['graph_version'] = new_graph.get('version', session['graph_version'] + 1)

            # Snapshot the current transcript - this is what was used to build this graph
            session['transcript_for_current_graph'] = session['full_transcript']

            # Update metadata
            now = datetime.utcnow().isoformat() + 'Z'
            session['metadata']['total_graph_updates'] += 1
            session['metadata']['last_update_at'] = now

            logger.info(
                f"Updated graph for session {session_id}: "
                f"version={session['graph_version']}, "
                f"nodes={len(new_graph.get('nodes', []))}, "
                f"edges={len(new_graph.get('edges', []))}"
            )

            return {
                'session_id': session_id,
                'graph': new_graph,
                'graph_version': session['graph_version'],
                'updated_at': now
            }

    def add_transcript_chunk(
        self,
        session_id: str,
        chunk_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Add a transcript chunk to the session.

        Args:
            session_id: Session ID
            chunk_data: Transcript chunk data from STT

        Returns:
            dict: Updated session info

        Raises:
            ValueError: If session doesn't exist
        """
        with self.lock:
            if session_id not in self.sessions:
                raise ValueError(f"Session {session_id} not found")

            session = self.sessions[session_id]

            # Add chunk to history
            session['transcript_chunks'].append(chunk_data)
            session['chunk_count'] += 1

            # Append to full transcript
            text = chunk_data.get('text', '')
            if text:
                if session['full_transcript']:
                    session['full_transcript'] += ' ' + text
                else:
                    session['full_transcript'] = text

            logger.debug(
                f"Added transcript chunk to session {session_id}: "
                f"chunk_id={chunk_data.get('chunk_id')}, "
                f"text_length={len(text)}"
            )

            return {
                'session_id': session_id,
                'chunk_count': session['chunk_count'],
                'full_transcript_length': len(session['full_transcript'])
            }

    def _save_session_to_disk_internal(self, session_id: str, session: Dict[str, Any]) -> str:
        """
        Internal method to save a session to disk. Assumes lock is already held.

        Args:
            session_id: Session ID to save
            session: Session data to save

        Returns:
            str: Path to saved file
        """
        # Create filename with timestamp
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"{session_id}_{timestamp}.json"
        filepath = os.path.join(self.save_directory, filename)

        # Save to disk
        try:
            with open(filepath, 'w') as f:
                json.dump(session, f, indent=2, default=str)

            logger.info(f"Saved session {session_id} to {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Failed to save session {session_id}: {e}")
            raise

    def save_session_to_disk(self, session_id: str) -> str:
        """
        Save a session to disk as JSON.

        Args:
            session_id: Session ID to save

        Returns:
            str: Path to saved file

        Raises:
            ValueError: If session doesn't exist
        """
        with self.lock:
            if session_id not in self.sessions:
                raise ValueError(f"Session {session_id} not found")

            session = self.sessions[session_id]
            return self._save_session_to_disk_internal(session_id, session)

    def stop_session(self, session_id: str) -> Dict[str, Any]:
        """
        Stop a session and save it to disk.

        Args:
            session_id: Session ID to stop

        Returns:
            dict: Final session state

        Raises:
            ValueError: If session doesn't exist
        """
        with self.lock:
            if session_id not in self.sessions:
                raise ValueError(f"Session {session_id} not found")

            session = self.sessions[session_id]

            now = datetime.utcnow().isoformat() + 'Z'
            session['status'] = 'stopped'
            session['stopped_at'] = now

            logger.info(
                f"Stopped session {session_id}: "
                f"chunks={session['chunk_count']}, "
                f"graph_version={session['graph_version']}"
            )

            # Save to disk (using internal method since we already hold the lock)
            try:
                filepath = self._save_session_to_disk_internal(session_id, session)
                saved_path = filepath
            except Exception as e:
                logger.error(f"Failed to save session to disk: {e}")
                saved_path = None

            return {
                'session_id': session_id,
                'status': 'stopped',
                'stopped_at': now,
                'saved_to': saved_path,
                'summary': {
                    'chunk_count': session['chunk_count'],
                    'graph_version': session['graph_version'],
                    'transcript_length': len(session['full_transcript']),
                    'total_graph_updates': session['metadata']['total_graph_updates']
                }
            }

    def pause_session(self, session_id: str) -> Dict[str, Any]:
        """
        Pause a session - stops audio capture but keeps state.

        Args:
            session_id: Session ID to pause

        Returns:
            dict: Updated session info

        Raises:
            ValueError: If session doesn't exist or is not active
        """
        with self.lock:
            if session_id not in self.sessions:
                raise ValueError(f"Session {session_id} not found")

            session = self.sessions[session_id]

            if session['status'] != 'active':
                raise ValueError(f"Can only pause active sessions (current: {session['status']})")

            # Calculate active duration
            if session['resumed_at']:
                last_active_str = session['resumed_at']
            else:
                last_active_str = session['started_at']

            last_active = datetime.fromisoformat(last_active_str.replace('Z', '+00:00'))
            now_dt = datetime.utcnow()
            active_duration = (now_dt - last_active.replace(tzinfo=None)).total_seconds()

            # Update session state
            now = datetime.utcnow().isoformat() + 'Z'
            session['status'] = 'paused'
            session['paused_at'] = now
            session['pause_count'] += 1

            logger.info(
                f"Paused session {session_id} "
                f"(pause #{session['pause_count']}, "
                f"was active for {active_duration:.1f}s)"
            )

            return {
                'session_id': session_id,
                'status': 'paused',
                'paused_at': now,
                'pause_count': session['pause_count'],
                'chunk_count': session['chunk_count'],
                'graph_version': session['graph_version']
            }

    def resume_session(self, session_id: str) -> Dict[str, Any]:
        """
        Resume a paused session - continues from current state.

        Args:
            session_id: Session ID to resume

        Returns:
            dict: Updated session info

        Raises:
            ValueError: If session doesn't exist or is not paused
        """
        with self.lock:
            if session_id not in self.sessions:
                raise ValueError(f"Session {session_id} not found")

            session = self.sessions[session_id]

            if session['status'] != 'paused':
                raise ValueError(f"Can only resume paused sessions (current: {session['status']})")

            # Calculate paused duration
            if session['paused_at']:
                paused_start = datetime.fromisoformat(session['paused_at'].replace('Z', '+00:00'))
                now_dt = datetime.utcnow()
                paused_duration = (now_dt - paused_start.replace(tzinfo=None)).total_seconds()
                session['total_paused_duration'] += paused_duration
            else:
                paused_duration = 0.0

            # Update session state
            now = datetime.utcnow().isoformat() + 'Z'
            session['status'] = 'active'
            session['resumed_at'] = now

            logger.info(
                f"Resumed session {session_id} "
                f"(was paused for {paused_duration:.1f}s, "
                f"total paused: {session['total_paused_duration']:.1f}s)"
            )

            return {
                'session_id': session_id,
                'status': 'active',
                'resumed_at': now,
                'pause_count': session['pause_count'],
                'total_paused_duration': session['total_paused_duration'],
                'chunk_count': session['chunk_count'],
                'graph_version': session['graph_version']
            }

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session from memory.

        Args:
            session_id: Session ID to delete

        Returns:
            bool: True if deleted, False if not found
        """
        with self.lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                logger.info(f"Deleted session: {session_id}")
                return True
            return False

    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all sessions (summary info only).

        Returns:
            dict: Map of session_id to session summary
        """
        with self.lock:
            summaries = {}
            for session_id, session in self.sessions.items():
                summaries[session_id] = {
                    'session_id': session_id,
                    'status': session['status'],
                    'created_at': session['created_at'],
                    'started_at': session['started_at'],
                    'stopped_at': session['stopped_at'],
                    'chunk_count': session['chunk_count'],
                    'graph_version': session['graph_version']
                }
            return summaries

    def get_stats(self) -> Dict[str, Any]:
        """
        Get orchestrator statistics.

        Returns:
            dict: Statistics
        """
        with self.lock:
            active_sessions = sum(1 for s in self.sessions.values() if s['status'] == 'active')
            stopped_sessions = sum(1 for s in self.sessions.values() if s['status'] == 'stopped')

            return {
                'total_sessions': len(self.sessions),
                'active_sessions': active_sessions,
                'stopped_sessions': stopped_sessions,
                'max_sessions': self.max_sessions
            }
