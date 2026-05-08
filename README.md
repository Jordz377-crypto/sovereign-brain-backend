# Sovereign Brain Backend — AI Automation Systems (PTY) LTD

Secure FastAPI backend connecting the Lovable frontend to the Groq AI engine with POPIA-compliant data privacy, RAG via Supabase pgvector, and n8n/Evolution API orchestration.

## Architecture

```
Lovable Frontend (React/TanStack)
       │
       ▼
┌──────────────────────────────┐
│    FastAPI (this service)    │
│                              │
│  ┌──────────┐ ┌───────────┐  │
│  │ AIGOS    │ │ Groq RAG  │  │
│  │ Shield   │ │ Engine     │  │
│  │ (POPIA)  │ │ (SSE)     │  │
│  └────┬─────┘ └─────┬─────┘  │
│       │              │        │
│  ┌────▼──────────────▼─────┐ │
│  │   Service Hub Endpoints  │ │
│  └────┬──────────────┬─────┘ │
└───────┼──────────────┼───────┘
        │              │
   ┌────▼───┐    ┌─────▼─────┐
   │Supabase│    │   n8n     │
   │pgvector│    │ Workflows │
   └────────┘    └─────┬─────┘
                       │
                  ┌────▼─────┐
                  │ Evolution │
                  │  API      │
                  │ (WhatsApp)│
                  └──────────┘
```

## Quick Start

### 1. Environment Setup

```bash
cp .env.example .env
```

Fill in your credentials in `.env`:

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Your Groq API key (gsk_...) |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key (server-side) |
| `EVOLUTION_API_TOKEN` | Evolution API token for WhatsApp |
| `N8N_WEBHOOK_URL` | Base URL for n8n webhooks |
| `REDIS_URL` | Redis connection string |
| `CORS_ORIGINS` | Comma-separated allowed origins |

### 2. Run with Docker (recommended)

```bash
docker-compose up --build
```

The API will be available at `http://localhost:8000`.

### 3. Run without Docker

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## API Endpoints

### POST /v1/chat — Secure AI Chat

Sends messages to Groq with POPIA-compliant sanitization and SSE streaming.

```json
{
  "messages": [
    { "role": "user", "content": "What services do you offer?" }
  ]
}
```

Response: Server-Sent Events stream (`text/event-stream`).

**Frontend note:** Update `api.ts` in the frontend to use `/v1/chat` instead of `/chat`.

### POST /v1/leads/capture — Lead Capture

Receives data from the AI Audit form and pushes it to Supabase + n8n.

```json
{
  "source": "audit",
  "name": "Client Name",
  "email": "client@example.com",
  "company": "Example Corp",
  "phone": "+27123456789",
  "hours_manual": 40,
  "pain_points": "Manual data entry taking too long"
}
```

### POST /v1/handoff — Human Handoff

Triggers a high-priority alert to the founders' WhatsApp channel.

```json
{
  "transcript": [
    { "role": "user", "content": "I want to speak to a human" },
    { "role": "assistant", "content": "Connecting you now..." }
  ],
  "contact_info": { "name": "Client", "email": "client@example.com" }
}
```

### GET /v1/system/health — Health Check

Returns API uptime, Groq availability, and Supabase connection status.

## AIGOS Security Layer

The AIGOS Shield (`app/security/aigos_shield.py`) intercepts every incoming request and:

1. **Jailbreak Detection** — Scores messages against known prompt injection patterns
2. **PII Redaction** — Detects and redacts South African ID numbers, phone numbers, email addresses, and physical addresses before they reach Groq
3. **Founders Guard** — Routes mentions of Jordan/Jevon in lead-gen contexts exclusively to internal n8n workflows
4. **Audit Logging** — Maintains an encrypted audit trail for POPIA compliance reporting

## Supabase Setup

### Required Tables

```sql
-- Leads table
CREATE TABLE leads (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  source TEXT NOT NULL,
  name TEXT,
  email TEXT,
  company TEXT,
  phone TEXT,
  hours_manual NUMERIC,
  pain_points TEXT,
  payload JSONB DEFAULT '{}'::jsonb
);

-- Trading performance table
CREATE TABLE trading_performance (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  symbol TEXT NOT NULL,
  position_size NUMERIC,
  entry_price NUMERIC,
  current_price NUMERIC,
  profit_loss NUMERIC,
  profit_loss_pct NUMERIC,
  timestamp TEXT,
  magic_number INT,
  comment TEXT
);

-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents table for RAG
CREATE TABLE documents (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  content TEXT NOT NULL,
  embedding VECTOR(1536),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Match documents function
CREATE OR REPLACE FUNCTION match_documents(
  query_embedding VECTOR(1536),
  match_count INT DEFAULT 5
) RETURNS TABLE(id UUID, content TEXT, similarity FLOAT) AS $$
BEGIN
  RETURN QUERY
  SELECT d.id, d.content, 1 - (d.embedding <=> query_embedding) AS similarity
  FROM documents d
  ORDER BY d.embedding <=> query_embedding
  LIMIT match_count;
END;
$$ LANGUAGE plpgsql;
```

### Row Level Security

For the frontend's direct Supabase inserts, enable RLS with:

```sql
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow anonymous inserts" ON leads FOR INSERT WITH CHECK (true);
```

## n8n Workflows

Three pre-built workflows are in `n8n-workflows/`:

1. **instant-lead-alert.json** — When a new lead appears in Supabase, sends WhatsApp to Jordan (+27 70 459 2553) and Jevon (+27 73 891 6611)
2. **email-confirmation.json** — Sends a professional "Next Steps" email from the J&J corporate domain
3. **human-handoff.json** — Alerts founders via dedicated WhatsApp channel when a client requests live interaction

Import these into your n8n instance via the UI (Workflows → Import from File).

## Security Headers

Every response includes:
- `X-AIGOS-Version` — Current API version
- `X-AIGOS-Provider` — AI Automation Systems (PTY) LTD
- `X-POPIA-Compliant` — POPIA compliance assertion
