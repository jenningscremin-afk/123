

Technical Design Document: Codex-VPA (Virtual Production Assistant)
1. Overview
This document specifies the architecture and design of the Codex-VPA (Virtual Production Assistant), an automated system for producing virtual human video courses. The system is designed to ingest structured course data and generate perfectly synchronized, high-quality video presentations with zero manual intervention during the recording phase. It prioritizes cost-efficiency, timing precision, and production quality to create a robust, industrial-grade workflow.

2. Goals and Non-Goals
2.1. Goals
G1: Flawless Automation: To provide a fully automated, event-driven playback mechanism that ensures perfect synchronization between virtual human speech, animations, and slide transitions.

G2: Cost Elimination: To prevent all unnecessary expenditure on the paid Virtual Human API through a comprehensive, zero-cost Rehearsal Mode and a Preflight Check system.

G3: Visual Fidelity: To support the implementation and management of complex, varied visualizations (both Canvas-based and DOM/CSS-based) in a modular and extensible manner.

G4: Production Efficiency: To enable a "One-Click Record" workflow after a successful rehearsal, eliminating the need for repetitive, time-consuming error correction and re-recording.

G5: Clean Output: To guarantee that the final video output is free of any non-content user interface elements.

2.2. Non-Goals
NG1: Content Creation GUI: This system will not provide a graphical user interface for creating or editing course content. Content is expected to be authored in JSON format.

NG2: Video Editing: This system will not perform post-production video editing (e.g., adding intros/outros, transitions between separate video files). Its scope ends at the creation of a single, complete video file for one lesson.

NG3: Direct MP4 Generation: The system's final output is a perfectly choreographed real-time HTML presentation ready for screen capture by an external tool. It does not contain an MP4 encoder.

3. System Architecture
The Codex-VPA employs a modular architecture composed of distinct, single-responsibility agents and modules. The interaction is managed by a central orchestrator.

Code snippet

graph TD
    subgraph Pre-Production
        A[course_data.json] --> B(ContentCompilerAgent);
        B --> C{presentation.html};
    end

    subgraph Production
        D(User) -- Clicks Button --> E(PlaybackOrchestrator);
        C --> F(PreflightCheckAgent);
        F -- Report --> E;
        E -- Uses --> G(AnimationFactory);
        E -- Calls --> H{Virtual Human SDK};
        G -- Creates --> I[Animation Modules];
    end

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style C fill:#ccf,stroke:#333,stroke-width:2px
4. Data Models
The entire system is driven by a master configuration object, typically loaded from course_data.json.

4.1. courseData Schema
JSON

{
  "totalSlides": "number",
  "subtitleScript": {
    "[slideNumber: string]": "string" // Contains script and action cues, e.g., "(动作: ID) text..."
  },
  "pageAnimations": {
    "[slideNumber: string]": {
      "module": "string", // Name of the animation class to be instantiated by AnimationFactory
      "params": "object", // Configuration for the animation (e.g., { stage: 'tangent' })
      "duration": "number" // Estimated duration for rehearsal and timeout purposes
    }
  },
  "pageBufferMs": "number" // Milliseconds to pause after a slide is fully complete
}
5. Agent Specifications
This section formally defines each agent within the Codex-VPA system.

Agent 5.1: ContentCompilerAgent

ID: VPA-COMPILER-01

Description: A pre-production agent that transforms the courseData.json into a runnable HTML presentation.

(Details as specified in the previous response)

Agent 5.2: PreflightCheckAgent

ID: VPA-DIAG-02

Description: A critical diagnostic agent that validates the courseData configuration to prevent runtime errors and wasted resources.

(Details as specified in the previous response, including all checks like continuity, MathJax syntax, and minimum duration)

Agent 5.3: AnimationFactory

ID: VPA-VISUAL-03

Description: A factory module that instantiates and returns the appropriate animation controller for a given slide based on the courseData configuration.

Pain Point Addressed: This is the core component that addresses the "ignoring complex visualizations" requirement. It provides a formal, extensible entry point for all visual effects.

(Details as specified in the previous response, including the switch-case logic for different animation types)

Agent 5.4: PlaybackOrchestrator

ID: VPA-CORE-04

Description: The master agent that executes the synchronized playback sequence. It operates in two modes: rehearse and record.

(Details as specified in the previous response)

6. Core Interaction Flow (Sequence Diagram)
This diagram illustrates the event-driven logic for rendering a single slide, which is the key to achieving perfect timing.

Code snippet

sequenceDiagram
    participant Orch as PlaybackOrchestrator
    participant Anim as AnimationModule
    participant SDK as VirtualHumanSDK
    
    Orch->>Anim: play()
    activate Anim
    Note right of Anim: Animation is running...
    Anim-->>Orch: Promise resolves (animation done)
    deactivate Anim
    
    Orch->>SDK: play(script)
    activate SDK
    Note right of SDK: Virtual human is speaking...
    SDK-->>Orch: onPlayEnd event (speech done)
    deactivate SDK
    
    Orch->>Orch: await sleep(buffer)
    Note over Orch: Waiting for buffer time...
    
    Orch->>Orch: Proceed to next slide
7. Risks and Mitigations
Risk 1: Virtual Human SDK API Changes: The third-party SDK is a critical external dependency. If its API (e.g., event names, method signatures) changes, it could break the event-driven logic.

Mitigation: All SDK interactions are isolated within the PlaybackOrchestrator. A dedicated adapter or wrapper function will be created for all SDK calls, minimizing the surface area that needs to be updated if the API changes.

Risk 2: Browser Performance Variability: On lower-end machines, complex Canvas animations or DOM updates could lag, potentially causing visual stutter even if the overall sequence timing is correct.

Mitigation: The Rehearsal Mode allows for testing on a target machine. Animation modules will be designed with performance in mind (e.g., using requestAnimationFrame for Canvas, leveraging hardware-accelerated CSS transforms). The event-driven model is inherently resilient to minor fluctuations, as it waits for tasks to complete.

Risk 3: Content Errors: Typos in courseData.json (e.g., incorrect module name, bad parameters) can cause runtime failures.

Mitigation: The PreflightCheckAgent is the primary mitigation. It is designed to catch as many configuration errors as possible before playback begins.