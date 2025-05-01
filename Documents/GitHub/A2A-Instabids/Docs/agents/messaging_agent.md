# PRD – MessagingAgent (InstaBids)

## 1. Purpose
Filters communications between homeowners and contractors based on platform rules, ensuring secure and appropriate messaging.

## 2. Key Capabilities

| Capability             | Details                                                                 |
|------------------------|-------------------------------------------------------------------------|
| **Message Filtering**  | Filter communications based on platform rules and policies              |
| **Content Moderation** | Ensure messages adhere to community guidelines                          |
| **PII Protection**     | Prevent sharing of personal identifiable information until connection   |
| **Bid Relay**          | Relay bid information from contractors to homeowners                    |
| **Question Handling**  | Facilitate Q&A between homeowners and contractors                       |
| **Notification**       | Send notifications about new messages and updates                       |
| **Connection Handling**| Manage the transition when a homeowner selects a contractor             |

## 3. Integration Points

- Receives messages from HomeownerAgent and ContractorAgent
- Filters and processes messages according to platform rules
- Stores message history in Supabase
- Triggers connection events when homeowner selects a contractor
