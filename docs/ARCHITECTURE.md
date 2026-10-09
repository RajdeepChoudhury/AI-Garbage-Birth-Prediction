# Architecture and diagrams

All diagrams use Mermaid, which GitHub renders automatically.

## System architecture

```mermaid
flowchart LR
    U[Browser] --> FE[React app served by nginx]
    FE -->|REST and JWT| API[FastAPI backend]
    API --> DB[(PostgreSQL)]
    API --> RD[(Redis rate limits)]
    API --> ML[Predictor service]
    ML --> ART[Trained models and SHAP]
    API -->|grounded prompts| GQ[Groq API]
    TR[Training job] --> ART
    DG[Synthetic data generator] --> TR
```

## Entity relationship diagram

```mermaid
erDiagram
    USERS ||--o{ REFRESH_TOKENS : owns
    USERS ||--o{ AUDIT_LOGS : performs
    USERS {
        int id PK
        string email
        string hashed_password
        string role
        bool is_active
        datetime created_at
    }
    REFRESH_TOKENS {
        string jti PK
        int user_id FK
        bool revoked
        datetime expires_at
    }
    AUDIT_LOGS {
        int id PK
        int user_id FK
        string action
        string detail
        datetime created_at
    }
    PREDICTIONS {
        int id PK
        int ward
        float latitude
        float longitude
        date forecast_date
        float predicted_volume
        string risk_level
        float hotspot_probability
        float urgency_score
        float confidence
        string recommended_cleaning_time
        date predicted_overflow_date
        json top_factors
        datetime created_at
    }
```

Predictions are not linked to users. Who created a forecast is recorded in the audit log.

## Workflow

```mermaid
flowchart TD
    A[Officer uploads ward CSV] --> B{Valid columns and values?}
    B -->|no| C[Return clear error]
    B -->|yes| D[Take latest row of each ward]
    D --> E[Build features]
    E --> F[Regressor predicts volume]
    E --> G[Classifier predicts risk and probabilities]
    E --> H[SHAP computes top factors]
    F --> I[Derive urgency, cleaning window, overflow date]
    G --> I
    I --> J[Store forecasts]
    J --> K[Dashboard map and ranking]
    J --> L[Assistant context]
```

## Use cases

```mermaid
flowchart LR
    C((Citizen)) --> V1[View forecasts and models]
    AN((Analyst)) --> V1
    AN --> P1[Run predictions]
    AN --> AS[Use the assistant]
    O((Officer)) --> V1
    O --> P1
    O --> AS
    O --> UP[Upload CSV data]
    AD((Admin)) --> UM[Manage users]
    AD --> AL[Read audit log]
    AD --> V1
    AD --> P1
    AD --> AS
    AD --> UP
```

## Sequence: upload, forecast, ask

```mermaid
sequenceDiagram
    actor Officer
    participant FE as React app
    participant API as FastAPI
    participant PR as Predictor
    participant DB as Database
    participant GQ as Groq

    Officer->>FE: Sign in
    FE->>API: POST /auth/login
    API-->>FE: Access and refresh tokens
    Officer->>FE: Choose CSV
    FE->>API: POST /data/upload
    API->>API: Validate file
    API->>PR: Predict latest row per ward
    PR-->>API: Forecasts with SHAP factors
    API->>DB: Store forecasts and audit entry
    API-->>FE: Summary of risk counts
    Officer->>FE: Ask why Ward 17 is high risk
    FE->>API: POST /assistant/ask
    API->>DB: Load latest forecasts
    API->>GQ: Prompt with forecast data
    GQ-->>API: Answer
    API-->>FE: Answer shown in chat
```
