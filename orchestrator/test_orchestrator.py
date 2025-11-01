#!/usr/bin/env python3
"""
Test script for the Orchestrator service.

Tests the complete pipeline:
  Speech-to-Text → Orchestrator → Graph-Generation

Usage:
    python test_orchestrator.py
"""

import sys
import time
import json
import requests
from datetime import datetime


# Configuration
ORCHESTRATOR_URL = "http://localhost:8003"
COLORS = {
    'GREEN': '\033[92m',
    'YELLOW': '\033[93m',
    'RED': '\033[91m',
    'BLUE': '\033[94m',
    'CYAN': '\033[96m',
    'END': '\033[0m',
    'BOLD': '\033[1m'
}


def print_header(text):
    """Print a section header."""
    print(f"\n{COLORS['BOLD']}{COLORS['CYAN']}{'=' * 60}{COLORS['END']}")
    print(f"{COLORS['BOLD']}{COLORS['CYAN']}{text}{COLORS['END']}")
    print(f"{COLORS['BOLD']}{COLORS['CYAN']}{'=' * 60}{COLORS['END']}\n")


def print_success(text):
    """Print success message."""
    print(f"{COLORS['GREEN']}✅ {text}{COLORS['END']}")


def print_info(text):
    """Print info message."""
    print(f"{COLORS['BLUE']}ℹ️  {text}{COLORS['END']}")


def print_warning(text):
    """Print warning message."""
    print(f"{COLORS['YELLOW']}⚠️  {text}{COLORS['END']}")


def print_error(text):
    """Print error message."""
    print(f"{COLORS['RED']}❌ {text}{COLORS['END']}")


def test_health_check():
    """Test health check endpoint."""
    print_header("Test 1: Health Check")

    try:
        response = requests.get(f"{ORCHESTRATOR_URL}/health", timeout=5)

        if response.status_code == 200:
            data = response.json()
            print_success("Orchestrator is healthy")
            print_info(f"Service: {data.get('service')}")
            print_info(f"Status: {data.get('status')}")

            deps = data.get('dependencies', {})
            stt = deps.get('speech_to_text', {})
            graph = deps.get('graph_generation', {})

            if stt.get('healthy'):
                print_success(f"Speech-to-Text healthy: {stt.get('url')}")
            else:
                print_error(f"Speech-to-Text NOT healthy: {stt.get('url')}")
                print_warning("Make sure STT service is running!")
                return False

            if graph.get('healthy'):
                print_success(f"Graph-Generation healthy: {graph.get('url')}")
            else:
                print_error(f"Graph-Generation NOT healthy: {graph.get('url')}")
                print_warning("Make sure Graph-Gen service is running!")
                return False

            stats = data.get('stats', {})
            print_info(f"Sessions: {stats.get('total_sessions')} total, {stats.get('active_sessions')} active")

            return True

        elif response.status_code == 503:
            data = response.json()
            print_warning("Orchestrator is degraded")
            print_error("One or more dependencies are unhealthy")
            return False

        else:
            print_error(f"Unexpected response: {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print_error(f"Cannot connect to orchestrator at {ORCHESTRATOR_URL}")
        print_info("Make sure the orchestrator is running:")
        print_info("  cd orchestrator/src && python main.py")
        return False

    except Exception as e:
        print_error(f"Health check failed: {e}")
        return False


def test_start_session():
    """Test starting a session."""
    print_header("Test 2: Start Session")

    try:
        response = requests.post(
            f"{ORCHESTRATOR_URL}/sessions/start",
            headers={'Content-Type': 'application/json'},
            timeout=10
        )

        if response.status_code == 201:
            data = response.json()
            session_id = data.get('session_id')

            print_success(f"Session started: {session_id}")
            print_info(f"Status: {data.get('status')}")
            print_info(f"STT Session: {data.get('stt_session_id')}")

            endpoints = data.get('endpoints', {})
            print_info("Endpoints:")
            for name, path in endpoints.items():
                print(f"   {name}: {path}")

            return session_id

        elif response.status_code == 503:
            print_error("Service unavailable")
            print_info("Check that STT service is running on port 8005")
            return None

        else:
            print_error(f"Failed to start session: {response.status_code}")
            print_info(f"Response: {response.text}")
            return None

    except Exception as e:
        print_error(f"Start session failed: {e}")
        return None


def test_stream_session(session_id, duration=20):
    """Test streaming from a session."""
    print_header(f"Test 3: Stream Session (for {duration} seconds)")

    print_info(f"Connecting to stream for session: {session_id}")
    print_info("Speak into your microphone now!")
    print_info(f"Will listen for {duration} seconds...\n")

    try:
        url = f"{ORCHESTRATOR_URL}/sessions/{session_id}/stream"

        with requests.get(url, stream=True, timeout=None) as response:
            if response.status_code != 200:
                print_error(f"Stream failed: {response.status_code}")
                return False

            print_success("Connected to stream!")
            print()

            start_time = time.time()
            event_count = 0

            for line in response.iter_lines():
                # Check timeout
                if time.time() - start_time > duration:
                    print_info(f"\n⏱️  {duration} seconds elapsed, stopping stream...")
                    break

                if not line:
                    continue

                line = line.decode('utf-8')

                if line.startswith('data: '):
                    data_str = line[6:]

                    try:
                        event = json.loads(data_str)
                        event_count += 1

                        print(f"{COLORS['BOLD']}Event #{event_count}:{COLORS['END']}")
                        print(f"  Type: {event.get('event_type')}")
                        print(f"  Timestamp: {event.get('timestamp')}")

                        transcript = event.get('transcript', {})
                        if transcript:
                            text = transcript.get('text', '')
                            chunk_id = transcript.get('chunk_id')
                            print(f"  Transcript #{chunk_id}: \"{text}\"")

                        graph = event.get('graph', {})
                        if graph:
                            nodes = graph.get('nodes', [])
                            edges = graph.get('edges', [])
                            version = graph.get('version')
                            print(f"  Graph v{version}: {len(nodes)} nodes, {len(edges)} edges")

                            if nodes:
                                print(f"    Nodes:")
                                for node in nodes[:3]:  # Show first 3
                                    print(f"      - {node.get('label')} ({node.get('type')})")
                                if len(nodes) > 3:
                                    print(f"      ... and {len(nodes) - 3} more")

                        if event.get('error'):
                            print_warning(f"  Error: {event.get('error')}")

                        print()

                    except json.JSONDecodeError:
                        print_warning(f"Invalid JSON: {data_str}")
                        continue

            if event_count > 0:
                print_success(f"Received {event_count} events")
                return True
            else:
                print_warning("No events received")
                print_info("Make sure you spoke into your microphone!")
                return False

    except Exception as e:
        print_error(f"Stream failed: {e}")
        return False


def test_get_state(session_id):
    """Test getting session state."""
    print_header("Test 4: Get Session State")

    try:
        response = requests.get(
            f"{ORCHESTRATOR_URL}/sessions/{session_id}/state",
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()

            print_success("Retrieved session state")
            print_info(f"Session ID: {data.get('session_id')}")
            print_info(f"Status: {data.get('status')}")
            print_info(f"Chunk count: {data.get('chunk_count')}")
            print_info(f"Graph version: {data.get('graph_version')}")

            transcript = data.get('full_transcript', '')
            if transcript:
                print_info(f"Full transcript ({len(transcript)} chars):")
                print(f"  \"{transcript[:200]}{'...' if len(transcript) > 200 else ''}\"")
            else:
                print_warning("No transcript recorded (did you speak?)")

            graph = data.get('graph')
            if graph:
                nodes = graph.get('nodes', [])
                edges = graph.get('edges', [])
                print_info(f"Graph: {len(nodes)} nodes, {len(edges)} edges")

                if nodes:
                    print_info("Nodes:")
                    for node in nodes[:5]:  # Show first 5
                        label = node.get('label')
                        node_type = node.get('type')
                        importance = node.get('importance', 0)
                        print(f"   - {label} ({node_type}, importance: {importance:.2f})")
                    if len(nodes) > 5:
                        print(f"   ... and {len(nodes) - 5} more nodes")

                if edges:
                    print_info("Edges:")
                    for edge in edges[:5]:  # Show first 5
                        source_id = edge.get('source')
                        target_id = edge.get('target')
                        edge_type = edge.get('type')

                        # Find node labels
                        source_node = next((n for n in nodes if n['id'] == source_id), None)
                        target_node = next((n for n in nodes if n['id'] == target_id), None)

                        source_label = source_node.get('label') if source_node else source_id
                        target_label = target_node.get('label') if target_node else target_id

                        print(f"   - {source_label} --[{edge_type}]-> {target_label}")
                    if len(edges) > 5:
                        print(f"   ... and {len(edges) - 5} more edges")
            else:
                print_warning("No graph generated yet")

            return True

        elif response.status_code == 404:
            print_error("Session not found")
            return False

        else:
            print_error(f"Failed to get state: {response.status_code}")
            return False

    except Exception as e:
        print_error(f"Get state failed: {e}")
        return False


def test_stop_session(session_id):
    """Test stopping a session."""
    print_header("Test 5: Stop Session")

    try:
        response = requests.post(
            f"{ORCHESTRATOR_URL}/sessions/{session_id}/stop",
            headers={'Content-Type': 'application/json'},
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()

            print_success(f"Session stopped: {session_id}")

            summary = data.get('summary', {})
            print_info(f"Total chunks: {summary.get('chunk_count')}")
            print_info(f"Graph version: {summary.get('graph_version')}")
            print_info(f"Transcript length: {summary.get('transcript_length')} chars")
            print_info(f"Graph updates: {summary.get('total_graph_updates')}")

            return True

        elif response.status_code == 404:
            print_error("Session not found")
            return False

        else:
            print_error(f"Failed to stop session: {response.status_code}")
            return False

    except Exception as e:
        print_error(f"Stop session failed: {e}")
        return False


def test_list_sessions():
    """Test listing all sessions."""
    print_header("Test 6: List All Sessions")

    try:
        response = requests.get(f"{ORCHESTRATOR_URL}/sessions", timeout=5)

        if response.status_code == 200:
            data = response.json()
            sessions = data.get('sessions', [])
            count = data.get('count', 0)

            print_success(f"Found {count} session(s)")

            if sessions:
                for session in sessions:
                    print_info(f"Session: {session.get('session_id')}")
                    print(f"   Status: {session.get('status')}")
                    print(f"   Chunks: {session.get('chunk_count')}")
                    print(f"   Graph version: {session.get('graph_version')}")
            else:
                print_info("No sessions found")

            return True

        else:
            print_error(f"Failed to list sessions: {response.status_code}")
            return False

    except Exception as e:
        print_error(f"List sessions failed: {e}")
        return False


def main():
    """Run all tests."""
    print(f"\n{COLORS['BOLD']}{COLORS['BLUE']}")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║          ORCHESTRATOR SERVICE TEST SUITE                 ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print(f"{COLORS['END']}\n")

    print_info(f"Testing orchestrator at: {ORCHESTRATOR_URL}")
    print_info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Test 1: Health check
    if not test_health_check():
        print_error("\n❌ Health check failed. Cannot proceed with tests.")
        print_info("\nMake sure all services are running:")
        print_info("  1. cd speech-to-text/src && python main.py")
        print_info("  2. cd graph-generation/segmentation && python main.py")
        print_info("  3. cd orchestrator/src && python main.py")
        sys.exit(1)

    # Test 2: Start session
    session_id = test_start_session()
    if not session_id:
        print_error("\n❌ Failed to start session. Cannot proceed.")
        sys.exit(1)

    # Test 3: Stream session
    stream_duration = 20  # seconds
    test_stream_session(session_id, duration=stream_duration)

    # Test 4: Get state
    test_get_state(session_id)

    # Test 5: Stop session
    test_stop_session(session_id)

    # Test 6: List sessions
    test_list_sessions()

    # Summary
    print_header("Test Summary")
    print_success("All tests completed!")
    print_info("\nNext steps:")
    print_info("  1. Build a frontend that connects to the orchestrator")
    print_info("  2. Visualize the unified transcript + graph stream")
    print_info("  3. Add features like session replay, export, etc.")
    print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{COLORS['YELLOW']}⚠️  Tests interrupted by user{COLORS['END']}")
        sys.exit(0)
