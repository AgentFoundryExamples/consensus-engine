# Roadmap Packet Component Architecture

This diagram shows the component hierarchy and data flow for the roadmap packet feature.

```mermaid
graph TD
    A[RunDashboard] -->|run completed| B[RoadmapPacket]
    B -->|data extraction| C[selectors.ts]
    
    C -->|extractProposal| D[ProposalData]
    C -->|extractDecision| E[DecisionData]
    C -->|extractPersonaReviews| F[PersonaReview[]]
    C -->|extractRisks| G[RiskItem[]]
    C -->|extractNextSteps| H[NextStep[]]
    C -->|extractAcceptanceCriteria| I[string[]]
    
    B -->|has minority reports| J[MinorityReport]
    B -->|user clicks button| K[PersonaReviewModal]
    B -->|optional| L[JsonToggle]
    
    K -->|displays| D
    K -->|displays| F
    
    L -->|sanitizes| C
    
    style B fill:#e1f5ff
    style J fill:#fff4e6
    style K fill:#f0f0f0
    style L fill:#f0f0f0
    style C fill:#e8f5e9
```

## Component Relationships

### Data Flow

```mermaid
sequenceDiagram
    participant RD as RunDashboard
    participant RP as RoadmapPacket
    participant SEL as selectors
    participant MR as MinorityReport
    participant PRM as PersonaReviewModal
    participant JT as JsonToggle
    
    RD->>RP: Pass run (RunDetailResponse)
    RP->>SEL: extractRoadmapSummary(run)
    SEL-->>RP: summary data
    RP->>SEL: extractDecision(run)
    SEL-->>RP: decision + minority reports
    
    alt Has minority reports
        RP->>MR: Pass minorityReports
        MR-->>RP: Render dissenting opinions
    end
    
    alt User clicks "View Details"
        RP->>SEL: extractProposal(run)
        SEL-->>RP: proposal data
        RP->>SEL: extractPersonaReviews(run)
        SEL-->>RP: reviews data
        RP->>PRM: Open modal with data
        PRM-->>RP: Modal displayed
        PRM->>PRM: Focus trap active
        PRM->>PRM: Escape key pressed
        PRM-->>RP: Modal closed, focus restored
    end
    
    alt User clicks "Show Raw JSON"
        RP->>JT: Pass run data
        JT->>SEL: sanitizeJsonForDisplay(run)
        SEL-->>JT: sanitized JSON
        JT-->>RP: Display formatted JSON
    end
```

## State Management

```mermaid
stateDiagram-v2
    [*] --> NoRun: Initial
    NoRun --> Running: User submits idea
    Running --> Completed: Pipeline finishes
    Running --> Failed: Error occurs
    
    Completed --> ViewingPacket: Display RoadmapPacket
    ViewingPacket --> ModalOpen: User clicks "View Details"
    ModalOpen --> ViewingPacket: Close modal
    
    ViewingPacket --> JsonExpanded: Toggle JSON
    JsonExpanded --> ViewingPacket: Toggle JSON
    
    Failed --> Retry: User clicks retry
    Retry --> Running: Resubmit
    
    state ViewingPacket {
        [*] --> ShowingSummary
        ShowingSummary --> ShowingRisks
        ShowingRisks --> ShowingNextSteps
        ShowingNextSteps --> ShowingCriteria
    }
    
    state ModalOpen {
        [*] --> ShowingProposal
        ShowingProposal --> ShowingReviews
        ShowingReviews --> ReviewExpanded: Click details
        ReviewExpanded --> ShowingReviews: Collapse
    }
```

## Component Props Flow

```mermaid
graph LR
    A[RunDetailResponse] -->|run| B[RoadmapPacket]
    
    B -->|minority reports| C[MinorityReport]
    B -->|isOpen, onClose, proposal, reviews| D[PersonaReviewModal]
    B -->|data, label| E[JsonToggle]
    
    C -->|reports: MinorityReport[]| C1[Render badges & sections]
    
    D -->|proposal: ProposalData| D1[Render proposal sections]
    D -->|reviews: PersonaReview[]| D2[Render persona reviews]
    
    E -->|data: Record<string, unknown>| E1[sanitizeJsonForDisplay]
    E1 -->|sanitized| E2[JSON.stringify]
    E2 -->|formatted| E3[Display in pre/code]
    
    style A fill:#fff9c4
    style B fill:#e1f5ff
    style C fill:#fff4e6
    style D fill:#f0f0f0
    style E fill:#f0f0f0
```

## User Interaction Flow

```mermaid
journey
    title User Views Roadmap Packet
    section Submit Idea
      User enters idea: 5: User
      User clicks submit: 5: User
      System queues run: 3: System
    section Processing
      System processes run: 3: System
      User sees progress: 4: User
      System completes run: 5: System
    section View Results
      User sees roadmap packet: 5: User
      User reads summary: 5: User
      User checks risks: 4: User
      User reviews next steps: 4: User
    section Detailed View
      User clicks "View Details": 5: User
      Modal opens: 5: System
      User reads proposal: 5: User
      User expands reviews: 5: User
      User presses Escape: 5: User
      Modal closes: 5: System
    section Optional Actions
      User toggles JSON: 3: User
      User views raw data: 3: User
      User copies for sharing: 4: User
```

## Accessibility Flow

```mermaid
graph TD
    A[User Tab Navigation] -->|Tab key| B{Focus on RoadmapPacket}
    B -->|Tab| C[View Details Button]
    C -->|Enter/Space| D[Modal Opens]
    D -->|Auto focus| E[Close Button]
    E -->|Tab| F[Modal Content]
    F -->|Tab cycles| G[Back to Close Button]
    
    D -->|Escape key| H[Modal Closes]
    H -->|Auto focus| C
    
    D -->|Click Backdrop| H
    E -->|Click| H
    
    I[Screen Reader] -->|Announces| J[Decision Status]
    J -->|Announces| K[Confidence Score]
    K -->|Announces| L[Minority Report Badge]
    L -->|Announces| M[Risks Count]
    
    style D fill:#e8f5e9
    style H fill:#e8f5e9
    style I fill:#fff9c4
```

## Data Extraction Pipeline

```mermaid
graph LR
    A[RunDetailResponse] -->|proposal JSON| B[extractProposal]
    A -->|decision JSON| C[extractDecision]
    A -->|persona_reviews| D[extractPersonaReviews]
    A -->|all data| E[extractRoadmapSummary]
    
    D -->|reviews| F[extractRisks]
    D -->|reviews| G[extractNextSteps]
    A -->|proposal| H[extractAcceptanceCriteria]
    
    B -->|ProposalData| I[PersonaReviewModal]
    C -->|DecisionData| J[Decision Badge]
    C -->|minorityReports| K[MinorityReport]
    D -->|PersonaReview[]| I
    E -->|RoadmapSummary| L[Packet Header]
    F -->|RiskItem[]| M[Risks Section]
    G -->|NextStep[]| N[Next Steps Section]
    H -->|string[]| O[Criteria Section]
    
    style A fill:#fff9c4
    style B fill:#e8f5e9
    style C fill:#e8f5e9
    style D fill:#e8f5e9
    style E fill:#e8f5e9
    style F fill:#e8f5e9
    style G fill:#e8f5e9
    style H fill:#e8f5e9
```

## Error Handling Strategy

```mermaid
graph TD
    A[Component Receives Data] -->|Check null/undefined| B{Data Valid?}
    B -->|No| C[Return Fallback Component]
    B -->|Yes| D{Check Status}
    
    D -->|Not completed| E[Show Pending Message]
    D -->|Completed| F{Extract Data}
    
    F -->|Try extractProposal| G{Success?}
    G -->|No| H[Use Fallback Values]
    G -->|Yes| I[Render Proposal]
    
    F -->|Try extractDecision| J{Success?}
    J -->|No| K[Use Default Decision]
    J -->|Yes| L[Render Decision]
    
    F -->|Try extractReviews| M{Success?}
    M -->|No| N[Empty Array]
    M -->|Yes| O[Render Reviews]
    
    H --> P[Display "Not provided yet"]
    N --> Q[Display "No reviews available"]
    
    style C fill:#ffebee
    style E fill:#fff9c4
    style H fill:#fff9c4
    style N fill:#fff9c4
    style P fill:#fff9c4
    style Q fill:#fff9c4
```

## Security & Sanitization

```mermaid
graph TD
    A[Raw Run Data] -->|contains| B{Sensitive Fields?}
    B -->|Yes| C[sanitizeJsonForDisplay]
    B -->|No| D[Pass Through]
    
    C -->|Scan for patterns| E[token, key, secret, password, auth, credential]
    E -->|Found| F[Replace with REDACTED]
    E -->|Not found| G[Keep Original Value]
    
    C -->|Recursively process| H{Is Object?}
    H -->|Yes| I[Process Each Property]
    H -->|No| J{Is Array?}
    J -->|Yes| K[Process Each Element]
    J -->|No| L[Return Value]
    
    F --> M[Sanitized Data]
    G --> M
    D --> M
    M --> N[JsonToggle Display]
    
    style A fill:#ffebee
    style C fill:#e8f5e9
    style F fill:#fff9c4
    style M fill:#e1f5ff
```
