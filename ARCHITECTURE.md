# Architecture

```mermaid
flowchart LR
    A[Lead Source] --> B[Lead Intake]
    B --> C[AI Qualification Layer]
    C --> D[Score 0-100]
    D --> E{Temperature}
    E -->|Hot| F[Priority Follow-up]
    E -->|Warm| G[Standard Follow-up]
    E -->|Cold| H[Nurture]
    F --> I[Personalized Outreach Draft]
    G --> I
    H --> I
    I --> J[Human Approval]
    J --> K[CRM Pipeline]
    K --> L[Prospect Reply]
    L --> M[AI Reply Intelligence]
    M --> N[Intent + Sentiment]
    N --> O[Stage Recommendation]
    O --> K
    K --> P[Revenue Dashboard]
    K --> Q[Weighted Forecast]
    K --> R[Audit Trail]
```

## Production extension
Lead source/webhook → n8n → AI qualification → HubSpot/Salesforce → approved email → reply webhook → AI intent classifier → CRM stage → Calendar → dashboard.
