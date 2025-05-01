# PRD – HomeownerAgent (InstaBids)

## 1. Purpose
A persistent, multimodal AI concierge that guides a homeowner from first idea to contractor selection.

## 2. Key Capabilities

| Capability             | Details                                                                 |
|------------------------|-------------------------------------------------------------------------|
| **Input Modes**        | • Image of project area (preferred)  • Voice chat  • Structured form     |
| **Vision Analysis**    | Use OpenAI Vision to derive surface/material cues & context from photos |
| **Dialog & Memory**    | Clarify requirements, remember preferences, maintain long-term state in `PersistentMemory` |
| **Job Classification** | Classify into one of 6 categories: _One-Off, Ongoing Service, Handyman, Labor-Only, Multi-Phase, Emergency_ |
| **Urgency Modifier**   | Tag as _Dream_, _Urgent_, or _Emergency_                                |
| **Project Structuring**| Break multi-phase tasks into sub-projects automatically                |
| **Data Persistence**   | Store structured record in Supabase `projects` table                    |
| **Event Emission**     | Emit `project.created` A2A envelope via `a2a_comm.send_envelope()`      |
| **Bid Relay Loop**     | Notify homeowner as bids arrive; facilitate comparisons and selections  |
| **Tracing**            | Use `enable_tracing("stdout")` for development and test visibility      |

## 3. Data Model (Supabase)

```sql
-- Projects submitted by homeowners
projects (
  id UUID PRIMARY KEY,
  user_id UUID,
  title TEXT,
  description TEXT,
  category TEXT,
  urgency TEXT,
  status TEXT,
  created_at TIMESTAMP
);

-- Project-related images
project_images (
  id UUID PRIMARY KEY,
  project_id UUID,
  url TEXT,
  type TEXT  -- 'current' or 'desired'
);

-- Persistent memory values
memories (
  id UUID PRIMARY KEY,
  user_id UUID,
  key TEXT,
  value TEXT,
  updated_at TIMESTAMP
);
