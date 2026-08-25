# Nebula
## Technical Requirements Document (TRD)

**Status:** Draft  
**Version:** 0.1  
**Authors:** Vivek Upadhayay  
**Last Updated:** 2026-07-27

---

# 1. Purpose

This document defines the technical architecture and engineering decisions behind Nebula.

The architecture prioritizes modularity, scalability, maintainability, and future extensibility.

---

# 2. Technology Stack

## Backend

- Python 3.13+
- FastAPI

---

## Validation

- Pydantic

---

## ORM

- SQLAlchemy

---

## Database

- PostgreSQL

---

## Cache

- Redis

---

## Background Workers

- Celery + Redis

---

## Vector Database

- Qdrant

---

## Object Storage

- S3 Compatible Storage

---

## Authentication

- JWT

---

## Containerization

- Docker
- Docker Compose

---

## Deployment

Initial

- Docker Compose
- VPS

Future

- Kubernetes

---

# 3. High-Level Architecture

```text
                 WhatsApp Cloud API
                         │
                  Webhook Service
                         │
                Conversation Service
                         │
                  AI Orchestrator
                         │
     ┌────────────┬─────────────┬─────────────┐
     │            │             │             │
 Memory Service   RAG      Tool Engine   Workflow Engine
     │            │             │             │
     └────────────┴─────────────┴─────────────┘
                         │
                 Integration Layer
                         │
                External Business APIs
```

---

# 4. Core Services

## API Gateway

Responsibilities

- Authentication
- Authorization
- Routing
- Rate Limiting

---

## Messaging Service

Responsibilities

- WhatsApp Webhooks
- Incoming Messages
- Outgoing Messages
- Retry Logic
- Delivery Tracking

---

## AI Orchestrator

Responsible for

- Prompt Construction
- Context Retrieval
- Tool Planning
- Tool Execution
- Response Generation

---

## Memory Service

Stores

- Conversations
- Contacts
- Session Context
- Business Metadata

---

## Knowledge Service

Responsible for

- Document Upload
- Parsing
- Chunking
- Embeddings
- Semantic Search

---

## Tool Engine

Every business capability is exposed as a Tool.

Standard Interface

```python
class Tool:

    name: str

    description: str

    parameters: dict

    async def execute(self):
        ...
```

Example Tools

- CreateLeadTool
- SendEmailTool
- SearchOrderTool
- BookMeetingTool
- GoogleSheetsTool

---

## Workflow Engine

Supported Nodes

- Trigger
- AI
- Condition
- Tool
- Delay
- Loop
- Human Approval
- End

---

## Integration Service

Initial Integrations

- Google Sheets
- Gmail
- Calendar
- REST APIs

Future Integrations

- Shopify
- Zoho
- HubSpot
- Stripe
- Razorpay
- Slack
- Discord

---

# 5. Suggested Project Structure

```text
backend/

├── app/
│
├── api/
│
├── auth/
│
├── ai/
│   ├── orchestrator.py
│   ├── planner.py
│   ├── memory.py
│   ├── rag.py
│   ├── prompts/
│   └── tools/
│
├── services/
│   ├── messaging/
│   ├── workflow/
│   ├── integrations/
│   └── knowledge/
│
├── db/
│
├── models/
│
├── repositories/
│
├── schemas/
│
├── workers/
│
├── utils/
│
├── tests/
│
├── docker/
│
└── docs/
```

---

# 6. Database Schema

Core Tables

- users
- businesses
- contacts
- conversations
- messages
- agents
- knowledge_documents
- knowledge_chunks
- embeddings
- workflows
- workflow_runs
- integrations
- audit_logs

---

# 7. AI Processing Pipeline

```text
Incoming Message

↓

Load Customer

↓

Retrieve Conversation

↓

Retrieve Memory

↓

Retrieve Knowledge

↓

Construct Prompt

↓

LLM

↓

Need Tool?

↓

Execute Tool

↓

LLM

↓

Generate Response

↓

Persist Memory

↓

Send Reply
```

---

# 8. REST API

## Health

GET /health

---

## Messaging

POST /webhook

POST /send

---

## Chat

POST /chat

---

## Knowledge

POST /knowledge/upload

GET /knowledge/search

---

## Workflow

POST /workflow/run

---

## Tools

POST /tool/run

---

## Conversations

GET /conversation/{id}

---

## Contacts

GET /contact/{id}

---

# 9. Logging

Every request should include

- Request ID
- Conversation ID
- Business ID
- Token Usage
- Latency
- Tool Calls
- AI Cost
- Status Code

Use structured JSON logging.

---

# 10. Security

- JWT Authentication
- Password Hashing
- RBAC
- Secret Management
- HTTPS
- Webhook Signature Verification
- Rate Limiting

---

# 11. Testing Strategy

## Unit Tests

- AI Orchestrator
- Memory Service
- Tool Engine
- Workflow Engine

---

## Integration Tests

- PostgreSQL
- Redis
- Webhooks
- Tool Execution
- Knowledge Retrieval

---

## Load Testing

Target

- 1,000+ concurrent conversations
- 100+ businesses
- High message throughput

---

# 12. Future Architecture

Planned Components

- Dashboard Backend
- Billing Service
- Multi-Agent Framework
- Plugin SDK
- Workflow Marketplace
- Event Bus
- Analytics Engine
- Voice AI
- Multi-Channel Messaging
- Kubernetes Deployment