#!/usr/bin/env python3
"""
Simple test script for the speech-to-text API.
No external dependencies needed beyond requests.

Usage:
    python test_simple.py
"""

import requests
import time
import json

API_URL = "http://localhost:8005"

def test_transcription():
    """Test the speech-to-text API with live recording."""

    print("🎤 Speech-to-Text Simple Test")
    print("=" * 60)

    # Step 1: Start a session
    print("\n1️⃣  Starting recording session...")
    try:
        response = requests.post(
            f"{API_URL}/sessions/start",
            headers={"Content-Type": "application/json"},
            json={}
        )
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Is it running on http://localhost:8005?")
        print("   Start the server with: cd src && python main.py")
        return

    if response.status_code != 201:
        print(f"❌ Failed to start session: {response.text}")
        return

    data = response.json()
    session_id = data['session_id']
    print(f"✅ Session started: {session_id}")
    print(f"   Chunk duration: {data['config']['chunk_duration']}s")

    # Step 2: Stream with manual polling
    print(f"\n2️⃣  Recording started...")
    print("🎙️  START SPEAKING NOW!")
    print("   Speak for at least 8-10 seconds")
    print("   This test will run for 30 seconds")
    print("-" * 60)

    # Use stream=True for SSE
    stream_url = f"{API_URL}/sessions/{session_id}/stream"

    try:
        with requests.get(stream_url, stream=True, timeout=35) as r:
            buffer = ""
            for chunk in r.iter_content(chunk_size=1, decode_unicode=True):
                if chunk:
                    buffer += chunk

                    # Check if we have a complete SSE message
                    if "\n\n" in buffer:
                        lines = buffer.split("\n\n")
                        buffer = lines[-1]  # Keep incomplete part

                        for message in lines[:-1]:
                            if message.startswith("data: "):
                                data_str = message[6:]  # Remove "data: " prefix
                                try:
                                    chunk_data = json.loads(data_str)

                                    # Check if it's an error
                                    if 'error' in chunk_data:
                                        print(f"⚠️  Error: {chunk_data.get('message', 'Unknown error')}")
                                        continue

                                    # Display transcript chunk
                                    print(f"\n[Chunk #{chunk_data['chunk_id']}] {chunk_data['timestamp']}")
                                    print(f"📝 {chunk_data['text']}")
                                    print("-" * 60)

                                except json.JSONDecodeError:
                                    pass  # Ignore invalid JSON

    except KeyboardInterrupt:
        print("\n\n⏹️  Interrupted by user...")
    except requests.exceptions.Timeout:
        print("\n\n⏹️  Recording timeout (30s)...")
    except Exception as e:
        print(f"\n❌ Stream error: {str(e)}")

    # Step 3: Stop the session
    print("\n3️⃣  Stopping session...")
    try:
        response = requests.post(
            f"{API_URL}/sessions/{session_id}/stop",
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Session stopped")
            print(f"\n📊 Final Results:")
            print(f"   Total chunks: {data['chunk_count']}")
            print(f"   Duration: {data['total_duration']:.1f}s")

            if data['full_transcript']:
                print(f"\n📄 Full Transcript:")
                print("-" * 60)
                print(data['full_transcript'])
                print("-" * 60)
            else:
                print("\n⚠️  No transcript recorded (maybe no audio detected?)")
        else:
            print(f"⚠️  Failed to stop session: {response.text}")
    except Exception as e:
        print(f"⚠️  Error stopping session: {str(e)}")

    print("\n✅ Test complete!")


if __name__ == "__main__":
    try:
        test_transcription()
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
