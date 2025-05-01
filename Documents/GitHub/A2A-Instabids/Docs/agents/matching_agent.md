# PRD – MatchingAgent (InstaBids)

## 1. Purpose
Connects homeowner projects with appropriate contractors based on project requirements, contractor capabilities, and geographic proximity.

## 2. Key Capabilities

| Capability             | Details                                                                 |
|------------------------|-------------------------------------------------------------------------|
| **Contractor Matching**| Match projects with qualified contractors based on skills and location  |
| **Proximity Analysis** | Consider geographic proximity for efficient contractor routing          |
| **Project Bundling**   | Identify opportunities to bundle nearby projects for contractor efficiency |
| **Availability Check** | Verify contractor availability before sending project notifications     |
| **Relevance Scoring**  | Score and rank contractors based on project relevance                   |
| **Notification**       | Notify matched contractors about new project opportunities              |

## 3. Integration Points

- Receives standardized bid cards from BidCardAgent
- Accesses contractor profiles and capabilities from database
- Sends project notifications to ContractorAgent
- Updates project status in Supabase
