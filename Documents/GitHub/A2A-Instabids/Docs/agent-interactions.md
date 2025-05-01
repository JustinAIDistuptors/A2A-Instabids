# InstaBids Agent Interaction Flows

This document details the interaction patterns between agents in the InstaBids platform using the A2A protocol. These flows represent the core business processes and demonstrate how agents collaborate to deliver platform functionality.

## 1. Project Creation Flow

```mermaid
sequenceDiagram
    participant H as Homeowner (UI)
    participant HA as HomeownerAgent
    participant BA as BidCardAgent
    participant MA as MatchingAgent

    H->>HA: Submit project request
    HA->>HA: Validate initial input
    HA->>BA: Send task: Create bid card
    Note over HA,BA: A2A Task: create_bid_card
    BA->>BA: Process project details
    BA->>BA: Analyze photos
    BA->>BA: Identify missing information
    BA->>HA: Request missing details (if any)
    Note over BA,HA: A2A Response: input_required
    HA->>H: Ask for additional details
    H->>HA: Provide missing information
    HA->>BA: Send updated details
    BA->>BA: Generate structured bid card
    BA->>HA: Return completed bid card
    Note over BA,HA: A2A Response: completed
    HA->>MA: Send task: Find matching contractors
    Note over HA,MA: A2A Task: find_contractors
    MA->>MA: Search contractor database
    MA->>MA: Apply matching algorithms
    MA->>MA: Sort by relevance
    MA->>HA: Return matching contractors
    Note over MA,HA: A2A Response: completed
    HA->>H: Confirm project creation and potential matches
```

## 2. Contractor Bidding Flow

```mermaid
sequenceDiagram
    participant C as Contractor (UI)
    participant CA as ContractorAgent
    participant MA as MatchingAgent
    participant BA as BidCardAgent

    MA->>CA: Notify of matching project
    Note over MA,CA: A2A Task: notify_project_match
    CA->>C: Alert to potential project
    C->>CA: Request project details
    CA->>BA: Retrieve bid card
    Note over CA,BA: A2A Task: get_bid_card
    BA->>CA: Return bid card data
    Note over BA,CA: A2A Response: completed
    CA->>CA: Analyze project requirements
    CA->>CA: Estimate appropriate pricing
    CA->>C: Present structured project details
    C->>CA: Submit bid information
    CA->>CA: Format bid according to standards
    CA->>MA: Send completed bid
    Note over CA,MA: A2A Task: submit_bid
    MA->>MA: Validate bid completeness
    MA->>MA: Record bid in database
    MA->>CA: Confirm bid submission
    Note over MA,CA: A2A Response: completed
    CA->>C: Display confirmation
```

## 3. Homeowner Review and Selection Flow

```mermaid
sequenceDiagram
    participant H as Homeowner (UI)
    participant HA as HomeownerAgent
    participant MA as MatchingAgent
    participant MSA as MessagingAgent
    participant CA as ContractorAgent

    H->>HA: Request to view bids
    HA->>MA: Retrieve bids for project
    Note over HA,MA: A2A Task: get_project_bids
    MA->>HA: Return all project bids
    Note over MA,HA: A2A Response: completed
    HA->>HA: Format bids for comparison
    HA->>H: Present bid comparison
    H->>HA: Request to contact contractor
    HA->>MSA: Initialize messaging thread
    Note over HA,MSA: A2A Task: create_messaging_thread
    MSA->>MSA: Set up filtered messaging
    MSA->>HA: Return messaging thread ID
    Note over MSA,HA: A2A Response: completed
    H->>HA: Send message to contractor
    HA->>MSA: Forward message
    Note over HA,MSA: A2A Task: send_message
    MSA->>MSA: Apply content filtering
    MSA->>CA: Deliver filtered message
    Note over MSA,CA: A2A Task: deliver_message
    CA->>C: Show message from homeowner
    H->>HA: Select winning bid
    HA->>MA: Record selection
    Note over HA,MA: A2A Task: select_bid
    MA->>MA: Update project status
    MA->>MA: Initiate payment process
    MA->>MSA: Authorize direct contact
    Note over MA,MSA: A2A Task: authorize_direct_contact
    MSA->>MSA: Remove messaging restrictions
    MA->>HA: Confirm selection processed
    Note over MA,HA: A2A Response: completed
    HA->>H: Show confirmation and next steps
```

## 4. Project Bundling Flow

```mermaid
sequenceDiagram
    participant MA as MatchingAgent
    participant BA1 as BidCardAgent (Project 1)
    participant BA2 as BidCardAgent (Project 2)
    participant CA as ContractorAgent

    MA->>MA: Identify nearby similar projects
    MA->>BA1: Retrieve project details
    Note over MA,BA1: A2A Task: get_bid_card
    BA1->>MA: Return project 1 details
    Note over BA1,MA: A2A Response: completed
    MA->>BA2: Retrieve project details
    Note over MA,BA2: A2A Task: get_bid_card
    BA2->>MA: Return project 2 details
    Note over BA2,MA: A2A Response: completed
    MA->>MA: Analyze compatibility for bundling
    MA->>MA: Calculate potential efficiency gain
    MA->>CA: Propose bundled projects
    Note over MA,CA: A2A Task: propose_project_bundle
    CA->>CA: Evaluate bundle feasibility
    CA->>CA: Calculate bundled pricing
    CA->>MA: Accept bundle proposal
    Note over CA,MA: A2A Response: completed
    MA->>MA: Create bundled project record
    MA->>BA1: Update project association
    Note over MA,BA1: A2A Task: update_project_bundle
    MA->>BA2: Update project association
    Note over MA,BA2: A2A Task: update_project_bundle
```

## 5. Messaging Flow with Filtering

```mermaid
sequenceDiagram
    participant H as Homeowner (UI)
    participant HA as HomeownerAgent
    participant MSA as MessagingAgent
    participant CA as ContractorAgent
    participant C as Contractor (UI)

    H->>HA: Send message to contractor
    HA->>MSA: Forward message
    Note over HA,MSA: A2A Task: process_message
    MSA->>MSA: Check connection status
    MSA->>MSA: Apply content filters
    Note over MSA: Remove phone, email, URLs
    MSA->>MSA: Check for circumvention attempts
    MSA->>MSA: Store message in thread
    MSA->>CA: Deliver filtered message
    Note over MSA,CA: A2A Task: deliver_message
    CA->>C: Display filtered message
    C->>CA: Reply to homeowner
    CA->>MSA: Forward reply
    Note over CA,MSA: A2A Task: process_message
    MSA->>MSA: Apply content filters
    MSA->>MSA: Store in conversation thread
    MSA->>HA: Deliver filtered reply
    Note over MSA,HA: A2A Task: deliver_message
    HA->>H: Display filtered reply
```

## 6. Project Visualization Flow

```mermaid
sequenceDiagram
    participant C as Contractor (UI)
    participant CA as ContractorAgent
    participant BA as BidCardAgent
    participant VA as VisualizationTool

    C->>CA: Request to create project visualization
    CA->>BA: Retrieve project photos
    Note over CA,BA: A2A Task: get_project_photos
    BA->>CA: Return project photos
    Note over BA,CA: A2A Response: completed
    CA->>CA: Analyze project requirements
    CA->>VA: Request visualization
    Note over CA,VA: Tool call with photos & specs
    VA->>VA: Generate before/after images
    VA->>CA: Return visualization images
    CA->>C: Present visualization for approval
    C->>CA: Approve visualization
    CA->>BA: Attach visualization to bid
    Note over CA,BA: A2A Task: update_bid_attachments
    BA->>BA: Associate images with bid
    BA->>CA: Confirm attachment
    Note over BA,CA: A2A Response: completed
```

## 7. Agent State Transitions

Each A2A task follows this lifecycle:

1. **Submitted**: Initial task received by agent
2. **Working**: Agent actively processing the request
3. **Input-Required**: Agent needs additional information (creates multi-turn interaction)
4. **Completed**: Task successfully finished
5. **Failed**: Task could not be completed
6. **Canceled**: Task terminated by request

Example state transitions for a bid card creation task:

```mermaid
stateDiagram-v2
    [*] --> Submitted: Task initiated
    Submitted --> Working: BidCardAgent processing
    Working --> Input-Required: Missing project details
    Input-Required --> Working: Details provided
    Working --> Completed: Bid card created
    Working --> Failed: Invalid project type
    Submitted --> Canceled: User cancels request
    Completed --> [*]
    Failed --> [*]
    Canceled --> [*]
```

## A2A Message Structure Examples

### 1. Task Submission (HomeownerAgent to BidCardAgent)

```json
{
  "jsonrpc": "2.0",
  "id": "task-12345",
  "method": "tasks/send",
  "params": {
    "id": "bid-card-task-67890",
    "message": {
      "role": "user",
      "parts": [
        {
          "type": "text",
          "text": "Create a bid card for a bathroom renovation project"
        },
        {
          "type": "data",
          "data": {
            "projectType": "bathroom_renovation",
            "location": {
              "city": "Austin",
              "state": "TX",
              "zip": "78704"
            },
            "timeline": {
              "startDate": "2025-07-01",
              "endDate": "2025-08-15"
            },
            "budget": {
              "min": 15000,
              "max": 25000,
              "currency": "USD"
            },
            "description": "Full renovation of master bathroom, including new shower, tub, vanity, and tile work."
          }
        },
        {
          "type": "file",
          "file": {
            "name": "bathroom_current.jpg",
            "mimeType": "image/jpeg",
            "bytes": "base64EncodedImageData..."
          }
        }
      ],
      "metadata": {
        "userId": "homeowner-123",
        "projectId": "project-456"
      }
    }
  }
}
```

### 2. Task Response (BidCardAgent to HomeownerAgent)

```json
{
  "jsonrpc": "2.0",
  "id": "task-12345",
  "result": {
    "id": "bid-card-task-67890",
    "status": {
      "state": "input-required",
      "message": {
        "role": "agent",
        "parts": [
          {
            "type": "text",
            "text": "Additional information needed: What are the dimensions of the bathroom? Do you want to keep the current layout or change it? Are there any specific fixtures or finishes you prefer?"
          }
        ]
      },
      "timestamp": "2025-04-19T15:30:45Z"
    }
  }
}
```

### 3. Completed Task (BidCardAgent to HomeownerAgent)

```json
{
  "jsonrpc": "2.0",
  "id": "task-12345",
  "result": {
    "id": "bid-card-task-67890",
    "status": {
      "state": "completed",
      "message": {
        "role": "agent",
        "parts": [
          {
            "type": "text",
            "text": "Bid card successfully created for your bathroom renovation project."
          },
          {
            "type": "data",
            "data": {
              "bidCardId": "bid-card-789",
              "projectType": "bathroom_renovation",
              "location": {
                "city": "Austin",
                "state": "TX",
                "zip": "78704",
                "coordinates": {
                  "lat": 30.2500,
                  "lng": -97.7500
                }
              },
              "timeline": {
                "startDate": "2025-07-01",
                "endDate": "2025-08-15",
                "estimatedDuration": "6 weeks"
              },
              "budget": {
                "min": 15000,
                "max": 25000,
                "currency": "USD"
              },
              "specifications": {
                "dimensions": {
                  "length": 12,
                  "width": 8,
                  "height": 9,
                  "unit": "feet"
                },
                "fixtures": ["shower", "tub", "vanity", "toilet"],
                "materials": ["ceramic tile", "glass shower door"],
                "layout": "existing layout with modifications",
                "special_requirements": "ADA compliant fixtures preferred"
              },
              "photos": [
                {
                  "id": "photo-123",
                  "type": "current_state",
                  "url": "/project-images/bathroom_current.jpg"
                },
                {
                  "id": "photo-124",
                  "type": "reference_style",
                  "url": "/project-images/bathroom_reference.jpg"
                }
              ]
            }
          }
        ]
      },
      "timestamp": "2025-04-19T16:15:22Z"
    },
    "artifacts": [
      {
        "name": "Bathroom Renovation Bid Card",
        "parts": [
          {
            "type": "text",
            "text": "Complete bid card for bathroom renovation project ready for contractor review"
          },
          {
            "type": "data",
            "data": {
              "bidCardFormatVersion": "1.2",
              "generatedDate": "2025-04-19T16:15:20Z",
              "projectId": "project-456",
              "status": "ready_for_bids"
            }
          }
        ],
        "index": 0
      }
    ]
  }
}
```

## 8. Error Handling Examples

### Network Error

```json
{
  "jsonrpc": "2.0",
  "id": "task-12345",
  "error": {
    "code": -32603,
    "message": "Internal error",
    "data": {
      "type": "NetworkError",
      "detail": "Failed to connect to MatchingAgent at endpoint: https://matching.instabids.com/a2a"
    }
  }
}
```

### Input Validation Error

```json
{
  "jsonrpc": "2.0",
  "id": "task-12345",
  "error": {
    "code": -32602,
    "message": "Invalid parameters",
    "data": {
      "type": "ValidationError",
      "detail": "Missing required field: projectType in bid card data"
    }
  }
}
```

### Authorization Error

```json
{
  "jsonrpc": "2.0",
  "id": "task-12345",
  "error": {
    "code": -32001,
    "message": "Unauthorized operation",
    "data": {
      "type": "AuthorizationError",
      "detail": "MessagingAgent cannot authorize direct contact without confirmed payment"
    }
  }
}
```

## 9. Integration with External Systems

InstaBids agents will need to interact with several external systems:

1. **Supabase Database**: For persistent storage of users, projects, bids, and messages
2. **Image Processing Services**: To analyze project photos
3. **Geolocation Services**: For project location and bundling
4. **Payment Processing**: To handle contractor connection fees
5. **Notification Services**: For email and push notifications

Example flow for image processing integration:

```mermaid
sequenceDiagram
    participant BA as BidCardAgent
    participant IP as Image Processing Service
    participant DB as Supabase Database

    BA->>IP: Send project photo for analysis
    Note over BA,IP: REST API call with image data
    IP->>IP: Analyze image content
    IP->>IP: Identify room type
    IP->>IP: Estimate dimensions
    IP->>IP: Detect fixtures
    IP->>BA: Return analysis results
    BA->>BA: Incorporate into bid card
    BA->>DB: Store processed image data
    Note over BA,DB: Store vector embeddings
```

## 10. A2A Implementation Considerations

When implementing these flows, keep in mind:

1. **Task IDs**: Maintain consistent task IDs across agent boundaries for traceability
2. **Error Handling**: Implement graceful failure recovery with clear error messages
3. **Timeouts**: Set appropriate timeouts for inter-agent communication
4. **Idempotency**: Design operations to be safely retryable in case of failures
5. **State Management**: Maintain appropriate agent state to handle multi-turn interactions
6. **Security**: Implement proper authentication between agents
7. **Monitoring**: Add comprehensive logging for debugging and performance analysis

## 11. Agent Development Roadmap

The implementation of these interaction flows should follow this sequential approach:

1. **Phase 1**: Core project creation and bid submission flows
   - HomeownerAgent + BidCardAgent interaction
   - Basic contractor matching

2. **Phase 2**: Messaging and selection flows
   - MessagingAgent with filtering
   - Payment integration
   - Bid selection and connection

3. **Phase 3**: Advanced features
   - Project bundling
   - Visualization tools
   - Recommendation systems

Each phase should include comprehensive testing of the A2A interactions to ensure reliability and performance.