# InstaBids Implementation Plan

This plan outlines the development phases for the InstaBids platform, leveraging the A2A protocol and Google's Agent Development Kit (ADK), referencing the local `knowledge-bases/A2A` and `knowledge-bases/adk-python` repositories.

**Overall Approach:**

Build the system iteratively, focusing on establishing the core A2A communication patterns first, then layering on agent-specific logic, and finally integrating the UI and database persistence.

**Phase 1: Foundation - A2A Protocol & Basic Agent Setup**

1.  **Define Core A2A Structures:**
    *   **Goal:** Establish the fundamental data types for tasks, messages, and artifacts based on the A2A specification.
    *   **Action:** Define Python data classes (using Pydantic) for `Task`, `Message`, `Artifact`, `Agent`, etc., mirroring `knowledge-bases/A2A/specification/json/a2a.json`.
    *   **Reference:** `knowledge-bases/A2A/samples/python/common/types.py`.
    *   **Location:** `src/a2a_types/core.py`
2.  **Implement A2A Client/Server:**
    *   **Goal:** Create the basic communication layer for agents to interact.
    *   **Action:** Implement client functions and a server (FastAPI-based) for request handling.
    *   **Reference:** `knowledge-bases/A2A/samples/python/common/client/`, `knowledge-bases/A2A/samples/python/common/server/`, `knowledge-bases/adk-python/tests/unittests/fast_api/`.
    *   **Location:** `src/a2a_comm/client.py`, `src/a2a_comm/server.py`
3.  **Basic Agent Scaffolding (ADK):**
    *   **Goal:** Create placeholder agent classes for `HomeownerAgent`, `BidCardAgent`, `ContractorAgent`, `MatchingAgent`, `MessagingAgent`.
    *   **Action:** Define initial classes inheriting from ADK base agents, implementing basic A2A endpoint methods.
    *   **Reference:** `knowledge-bases/adk-python/src/google/adk/agents/`, `knowledge-bases/A2A/samples/python/agents/google_adk/`.
    *   **Location:** `src/agents/` (subdirectories for each agent)
4.  **Initial Supabase Schema:**
    *   **Goal:** Set up the database and define initial tables.
    *   **Action:** Create Supabase project. Define basic tables for `users`, `projects`, `bids`.
    *   **Reference:** Standard database design principles.

**Phase 2: Homeowner & Project Creation Flow**

1.  **Develop `HomeownerAgent` Logic:**
    *   **Goal:** Implement agent for guiding project creation.
    *   **Action:** Use ADK flows/logic, define prompts, integrate tools if needed.
    *   **Reference:** `knowledge-bases/adk-python/src/google/adk/agents/`, `flows/`, `tools/`.
2.  **Implement Project Persistence:**
    *   **Goal:** Save project details to Supabase.
    *   **Action:** Add Supabase client logic to `HomeownerAgent` or a data service. Handle artifact storage.
3.  **Develop `BidCardAgent`:**
    *   **Goal:** Standardize project info into a "Bid Card" artifact.
    *   **Action:** Create agent to transform raw project data into a structured JSON artifact.
    *   **Reference:** A2A specification for artifact structure.

**Phase 3: Contractor, Bidding & Matching**

1.  **Develop `ContractorAgent` Logic:**
    *   **Goal:** Implement agent for finding projects and submitting bids.
    *   **Action:** Fetch Bid Cards, guide bid creation, potentially use tools.
2.  **Implement Bid Persistence:**
    *   **Goal:** Save contractor bids to Supabase.
    *   **Action:** Add Supabase client logic to `ContractorAgent`.
3.  **Develop `MatchingAgent`:**
    *   **Goal:** Connect projects to contractors.
    *   **Action:** Implement matching logic (simple criteria initially, vector search later). Handle bundling.
    *   **Action:** Implement multi-tiered matching logic:
        *   Tier 1: Query registered contractors (`contractor_profiles`).
        *   Tier 2: Query known prospects (`prospect_contractors` table - requires schema addition).
        *   Tier 3: Integrate external search (e.g., Google Maps/Search tool) if needed based on urgency/target bids.
    *   Implement logic to track bid progress for assigned projects (e.g., check `bids` table or listen for events) and potentially re-trigger searches or outreach based on urgency/timeline.
    *   Handle project bundling logic.
    *   **Output:** List of registered contractor IDs (for direct notification) and prospect/new lead contact info (to be passed to `OutreachAgent`).
    *   **Reference:** Supabase documentation, Google Maps/Search API/Tool documentation.
4.  **Develop `OutreachAgent`:**
    *   **Goal:** Contact non-registered contractors identified by `MatchingAgent`.
    *   **Action:** Define agent structure. Implement methods/tools for outreach via:
        *   Email (using an email service/API).
        *   SMS (using an SMS service/API).
        *   Web Form Filling (using browser automation tool/library).
    *   Receive tasks from `MatchingAgent` with contact info and project context.
    *   Track outreach attempts and responses (potentially update `prospect_contractors` table).
    *   **Location:** `src/agents/outreach/`

**Phase 4: Communication & Security**

1.  **Develop `MessagingAgent`:**
    *   **Goal:** Manage and filter communication based on bid status.
    *   **Action:** Implement agent as intermediary, enforce communication rules.
    *   **Reference:** A2A message structures.
2.  **Implement A2A Message Routing:**
    *   **Goal:** Route messages through `MessagingAgent`.
    *   **Action:** Update A2A server logic to direct `create_message` requests.
3.  **Integrate Authentication:**
    *   **Goal:** Secure agent endpoints.
    *   **Action:** Implement auth mechanism using ADK handlers.
    *   **Reference:** `knowledge-bases/adk-python/src/google/adk/auth/`.

**Phase 5: UI Integration & Deployment**

1.  **Develop React Frontend:**
    *   **Goal:** Build the user interface.
    *   **Action:** Create React components for core user flows.
2.  **Connect UI to Backend:**
    *   **Goal:** Enable UI interaction with agents.
    *   **Action:** Expose A2A actions via an API gateway.
3.  **Deployment:**
    *   **Goal:** Deploy agents and UI.
    *   **Action:** Containerize agents, deploy to Vertex AI Agent Engine (or Cloud Run), deploy React frontend, set up CI/CD.
