# PRD – ContractorAgent (InstaBids)

## 1. Purpose
Helps contractors create accurate bids and visualizations for homeowner projects, streamlining the bidding process.

## 2. Key Capabilities

| Capability             | Details                                                                 |
|------------------------|-------------------------------------------------------------------------|
| **Bid Creation**       | Guide contractors through creating detailed, accurate bids              |
| **Cost Estimation**    | Assist with material and labor cost calculations                        |
| **Timeline Planning**  | Help contractors establish realistic project timelines                  |
| **Visualization**      | Generate visual representations of completed projects                   |
| **Communication**      | Facilitate clear communication with homeowners                          |
| **Bid Submission**     | Submit completed bids to homeowners through the platform               |
| **Memory Integration** | Use PersistentMemory to recall contractor preferences and past bids     |

## 3. Integration Points

- Receives project notifications from MatchingAgent
- Submits bids to homeowners via MessagingAgent
- Stores bid data in Supabase
- Accesses contractor profile information
