/**
 * Mock graph updates for testing SSE streaming
 *
 * Simulates incremental graph updates as they would arrive from the orchestrator
 */

const mockUpdates = [
  // Update 1: Initial graph (same as static-graph.json)
  {
    chunk_id: 0,
    timestamp: "2025-11-01T10:00:00Z",
    transcript: {
      text: "Okay, so let's talk about the mobile app redesign. I think we really need to focus on user experience, especially for first-time users. The onboarding flow is confusing right now.",
      speaker: "Speaker 1"
    },
    graph: {
      session_id: "test-session-001",
      version: 1,
      timestamp: "2025-11-01T10:00:00Z",
      nodes: [
        {
          id: "node-1",
          label: "Mobile App",
          type: "topic",
          importance: 0.9,
          color: "#8B5CF6",
          description: "Main mobile application project"
        },
        {
          id: "node-2",
          label: "User Experience",
          type: "concept",
          importance: 0.85,
          color: "#10B981",
          description: "Focus on improving UX design"
        },
        {
          id: "node-3",
          label: "Onboarding Flow",
          type: "concept",
          importance: 0.7,
          color: "#10B981",
          description: "First-time user onboarding experience"
        },
        {
          id: "node-4",
          label: "Performance Testing",
          type: "action",
          importance: 0.6,
          color: "#F59E0B",
          description: "Need to test app performance"
        },
        {
          id: "node-5",
          label: "Design Team",
          type: "person",
          importance: 0.5,
          color: "#EC4899",
          description: "Responsible for UI/UX design"
        }
      ],
      edges: [
        {
          id: "edge-1",
          source: "node-2",
          target: "node-1",
          type: "supports",
          strength: 0.9
        },
        {
          id: "edge-2",
          source: "node-3",
          target: "node-2",
          type: "elaborates",
          strength: 0.8
        },
        {
          id: "edge-3",
          source: "node-4",
          target: "node-1",
          type: "relates_to",
          strength: 0.7
        },
        {
          id: "edge-4",
          source: "node-5",
          target: "node-2",
          type: "relates_to",
          strength: 0.75
        }
      ]
    }
  },

  // Update 2: Add React Native concept + new edges
  {
    chunk_id: 1,
    timestamp: "2025-11-01T10:00:08Z",
    transcript: {
      text: "Actually, we should also consider using React Native for the mobile app. This will help with cross-platform development.",
      speaker: "Speaker 2"
    },
    graph: {
      session_id: "test-session-001",
      version: 2,
      timestamp: "2025-11-01T10:00:08Z",
      nodes: [
        {
          id: "node-1",
          label: "Mobile App",
          type: "topic",
          importance: 0.95,  // Increased (mentioned again)
          color: "#8B5CF6"
        },
        {
          id: "node-2",
          label: "User Experience",
          type: "concept",
          importance: 0.85,
          color: "#10B981"
        },
        {
          id: "node-3",
          label: "Onboarding Flow",
          type: "concept",
          importance: 0.7,
          color: "#10B981"
        },
        {
          id: "node-4",
          label: "Performance Testing",
          type: "action",
          importance: 0.6,
          color: "#F59E0B"
        },
        {
          id: "node-5",
          label: "Design Team",
          type: "person",
          importance: 0.5,
          color: "#EC4899"
        },
        {
          id: "node-6",  // NEW NODE
          label: "React Native",
          type: "concept",
          importance: 0.8,
          color: "#10B981",
          description: "Cross-platform mobile framework"
        },
        {
          id: "node-7",  // NEW NODE
          label: "Cross-Platform Development",
          type: "concept",
          importance: 0.75,
          color: "#10B981",
          description: "Build for iOS and Android simultaneously"
        }
      ],
      edges: [
        {
          id: "edge-1",
          source: "node-2",
          target: "node-1",
          type: "supports",
          strength: 0.9
        },
        {
          id: "edge-2",
          source: "node-3",
          target: "node-2",
          type: "elaborates",
          strength: 0.8
        },
        {
          id: "edge-3",
          source: "node-4",
          target: "node-1",
          type: "relates_to",
          strength: 0.7
        },
        {
          id: "edge-4",
          source: "node-5",
          target: "node-2",
          type: "relates_to",
          strength: 0.75
        },
        {
          id: "edge-5",  // NEW EDGE
          source: "node-6",
          target: "node-1",
          type: "supports",
          strength: 0.85
        },
        {
          id: "edge-6",  // NEW EDGE
          source: "node-7",
          target: "node-6",
          type: "elaborates",
          strength: 0.8
        }
      ]
    }
  },

  // Update 3: Add device testing + update importance
  {
    chunk_id: 2,
    timestamp: "2025-11-01T10:00:16Z",
    transcript: {
      text: "We'll need to test the performance on different devices to make sure it meets our requirements. Let's prioritize iOS first.",
      speaker: "Speaker 1"
    },
    graph: {
      session_id: "test-session-001",
      version: 3,
      timestamp: "2025-11-01T10:00:16Z",
      nodes: [
        {
          id: "node-1",
          label: "Mobile App",
          type: "topic",
          importance: 0.95,
          color: "#8B5CF6"
        },
        {
          id: "node-2",
          label: "User Experience",
          type: "concept",
          importance: 0.85,
          color: "#10B981"
        },
        {
          id: "node-3",
          label: "Onboarding Flow",
          type: "concept",
          importance: 0.7,
          color: "#10B981"
        },
        {
          id: "node-4",
          label: "Device Testing",  // Label refined (was "Performance Testing")
          type: "action",
          importance: 0.75,  // Increased (mentioned again)
          color: "#F59E0B",
          description: "Test on multiple device types"
        },
        {
          id: "node-5",
          label: "Design Team",
          type: "person",
          importance: 0.5,
          color: "#EC4899"
        },
        {
          id: "node-6",
          label: "React Native",
          type: "concept",
          importance: 0.8,
          color: "#10B981"
        },
        {
          id: "node-7",
          label: "Cross-Platform Development",
          type: "concept",
          importance: 0.75,
          color: "#10B981"
        },
        {
          id: "node-8",  // NEW NODE
          label: "iOS Priority",
          type: "decision",
          importance: 0.7,
          color: "#3B82F6",
          description: "Prioritize iOS platform first"
        }
      ],
      edges: [
        {
          id: "edge-1",
          source: "node-2",
          target: "node-1",
          type: "supports",
          strength: 0.9
        },
        {
          id: "edge-2",
          source: "node-3",
          target: "node-2",
          type: "elaborates",
          strength: 0.8
        },
        {
          id: "edge-3",
          source: "node-4",
          target: "node-1",
          type: "relates_to",
          strength: 0.8  // Increased strength
        },
        {
          id: "edge-4",
          source: "node-5",
          target: "node-2",
          type: "relates_to",
          strength: 0.75
        },
        {
          id: "edge-5",
          source: "node-6",
          target: "node-1",
          type: "supports",
          strength: 0.85
        },
        {
          id: "edge-6",
          source: "node-7",
          target: "node-6",
          type: "elaborates",
          strength: 0.8
        },
        {
          id: "edge-7",  // NEW EDGE
          source: "node-8",
          target: "node-4",
          type: "relates_to",
          strength: 0.75
        },
        {
          id: "edge-8",  // NEW EDGE
          source: "node-8",
          target: "node-1",
          type: "supports",
          strength: 0.7
        }
      ]
    }
  }
];

// Export for use in test page
if (typeof module !== 'undefined' && module.exports) {
  module.exports = mockUpdates;
}
