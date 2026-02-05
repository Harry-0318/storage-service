# ProjectAlpha Storage Service — Developer Documentation

> **Version**: 1.0  
> **Last Updated**: 2026-02-05  
> **Base URL**: `https://storage.projectalpha.in` (production)

---

## SECTION 1 — SYSTEM OVERVIEW

### What Is This Service?

ProjectAlpha Storage Service is a **centralized JSON storage backend** that allows multiple tools and applications to persist structured JSON data without managing their own databases.

### Core Purpose

- Store JSON payloads from various tools
- Provide schema-validated, isolated storage per tool
- Enable dynamic table creation without manual database migrations

### Two Storage Modes

| Mode | Endpoint | Use Case |
|------|----------|----------|
| **Common Storage** | `POST /common` | Small tools, low-sensitivity data, no schema enforcement |
| **Tool-Specific Storage** | `/tools/{tool_id}` | Larger tools, schema validation, isolated tables |

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Storage Service                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐     ┌──────────────────────────────┐  │
│  │  multiple_tools  │     │      registered_tools        │  │
│  │  (shared table)  │     │    (tool registry/metadata)  │  │
│  └──────────────────┘     └──────────────────────────────┘  │
│                                    │                         │
│                                    ▼                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │   tool_survey_bot   │   tool_analytics   │   ...     │   │
│  │   (dynamic tables created per registered tool)       │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### How Tools Are Registered and Accessed

1. Admin calls `POST /register-tool` with tool name, token, and schema
2. System creates entry in `registered_tools` table
3. System creates dedicated PostgreSQL table `tool_{tool_name}`
4. Tool uses `POST /tools/{tool_name}` with its token to store data
5. Anyone can read via `GET /tools/{tool_name}`

---

## SECTION 2 — CORE CONCEPTS

### 2.1 Tool Name vs Table Name

| Concept | Example | Where Used |
|---------|---------|------------|
| **tool_name** | `survey_bot` | API URLs, registration body, headers |
| **table_name** | `tool_survey_bot` | Actual PostgreSQL table (prefixed with `tool_`) |

> **⚠️ Common Mistake**: Developers try to query `survey_bot` table directly in SQL. The actual table is `tool_survey_bot`.

### 2.2 Tokens

The system uses **two distinct token types**:

#### Admin Token
- **Value**: `admin-secret-123` (hardcoded in `auth.py`)
- **Header**: `admin-token`
- **Required For**: Registering tools, deleting tools
- **Storage**: Hardcoded constant (not per-tool)

#### Tool Token
- **Value**: User-defined during registration (e.g., `my-secure-token-xyz`)
- **Header**: `token`
- **Required For**: Storing data to a specific tool
- **Storage**: Stored in `registered_tools.token` column per tool

#### Legacy Common Token
- **Values**: `token123`, `token456` (in `VALID_TOKENS` dict)
- **Header**: `token`
- **Required For**: `POST /common` with `sensitive: 1`
- **Storage**: Hardcoded in `auth.py`

### 2.3 Schema Validation System

#### Supported Types

| Type String | SQLAlchemy Type | Python Type Check |
|-------------|-----------------|-------------------|
| `int`, `integer` | `Integer` | `isinstance(value, int)` |
| `str`, `string` | `String` | `isinstance(value, str)` |
| `bool`, `boolean` | `Boolean` | `isinstance(value, bool)` |
| `float` | `Float` | No runtime check |
| `json` | `JSON` | No runtime check |
| `timestamp` | `TIMESTAMP` | No runtime check |

#### Validation Behavior

- **Schema Validation** (on registration): Checks that all fields have `name` and `type`, and type is supported
- **Payload Validation** (on insert): Checks `int`, `str`, `bool` types only
- **Extra Fields**: Silently ignored (not rejected)
- **Missing Fields**: Allowed (columns will be NULL)

---

## SECTION 3 — AUTHENTICATION MODEL

### Endpoint Authentication Summary

| Endpoint | Method | Auth Required | Header | Token Source |
|----------|--------|---------------|--------|--------------|
| `POST /common` | POST | Conditional (if `sensitive=1`) | `token` | `VALID_TOKENS` in `auth.py` |
| `POST /register-tool` | POST | **Required** | `admin-token` | `ADMIN_TOKEN` constant |
| `POST /tools/{tool_id}` | POST | **Required** | `token` | `registered_tools.token` |
| `GET /tools/{tool_id}` | GET | **None** | — | — |
| `DELETE /tools/{tool_id}` | DELETE | **Required** | `admin-token` | `ADMIN_TOKEN` constant |

### Header Format

```
admin-token: admin-secret-123
token: your-tool-specific-token
```

### Failure Responses

| Scenario | Status Code | Response Body |
|----------|-------------|---------------|
| Missing admin-token | 422 | `{"detail": [{"loc": ["header", "admin-token"], "msg": "field required", ...}]}` |
| Invalid admin-token | 403 | `{"detail": "Forbidden: Admin access only"}` |
| Missing tool token | 422 | `{"detail": [{"loc": ["header", "token"], "msg": "field required", ...}]}` |
| Invalid tool token | 401 | `{"detail": "Unauthorized: Invalid token for this tool"}` |
| Invalid common token | 401 | `{"detail": "Unauthorized: invalid or missing token"}` |

---

## SECTION 4 — ENDPOINT REFERENCE

---

### 4.1 Register Tool

**Purpose**: Create a new tool with dedicated storage table.

| Property | Value |
|----------|-------|
| **Method** | `POST` |
| **URL** | `/register-tool` |
| **Auth** | `admin-token` header required |

#### Headers

```
Content-Type: application/json
admin-token: admin-secret-123
```

#### Request Body

```json
{
  "tool_name": "survey_bot",
  "token": "survey-secure-token-001",
  "schema": [
    {"name": "user_id", "type": "int"},
    {"name": "feedback", "type": "str"},
    {"name": "rating", "type": "int"}
  ]
}
```

#### Example curl

```bash
curl -X POST "https://storage.projectalpha.in/register-tool" \
  -H "Content-Type: application/json" \
  -H "admin-token: admin-secret-123" \
  -d '{
    "tool_name": "survey_bot",
    "token": "survey-secure-token-001",
    "schema": [
      {"name": "user_id", "type": "int"},
      {"name": "feedback", "type": "str"}
    ]
  }'
```

#### Success Response (200)

```json
{"message": "Tool 'survey_bot' registered and table created"}
```

#### Failure Responses

| Condition | Status | Body |
|-----------|--------|------|
| Tool already exists | 400 | `{"detail": "Tool 'survey_bot' already registered"}` |
| Invalid schema | 400 | `{"detail": "Each field must have 'name' and 'type'"}` |
| Unsupported type | 400 | `{"detail": "Unsupported type: xyz. Allowed: ['int', 'integer', ...]"}` |
| Wrong admin token | 403 | `{"detail": "Forbidden: Admin access only"}` |
| Table creation fails | 500 | `{"detail": "Failed to create table: ..."}` |

---

### 4.2 Store Data

**Purpose**: Insert a record into a tool's dedicated table.

| Property | Value |
|----------|-------|
| **Method** | `POST` |
| **URL** | `/tools/{tool_id}` |
| **Auth** | `token` header (tool-specific) |

#### Headers

```
Content-Type: application/json
token: survey-secure-token-001
```

#### Request Body

Any JSON matching the registered schema:

```json
{
  "user_id": 42,
  "feedback": "Great product!"
}
```

#### Example curl

```bash
curl -X POST "https://storage.projectalpha.in/tools/survey_bot" \
  -H "Content-Type: application/json" \
  -H "token: survey-secure-token-001" \
  -d '{
    "user_id": 42,
    "feedback": "Great product!"
  }'
```

#### Success Response (200)

```json
{"message": "Data stored successfully"}
```

#### Failure Responses

| Condition | Status | Body |
|-----------|--------|------|
| Tool not found | 404 | `{"detail": "Tool not found"}` |
| Wrong token | 401 | `{"detail": "Unauthorized: Invalid token for this tool"}` |
| Type mismatch | 400 | `{"detail": "Field 'user_id' expected int, got <class 'str'>"}` |
| DB error | 500 | `{"detail": "..."}` |

#### Edge Cases

- **Extra fields in payload**: Silently ignored, not stored
- **Missing fields**: Stored as NULL in database
- **Empty payload `{}`**: Inserts row with only auto-generated `id` and `created_at`

---

### 4.3 Retrieve Data

**Purpose**: Fetch records from a tool's table.

| Property | Value |
|----------|-------|
| **Method** | `GET` |
| **URL** | `/tools/{tool_id}` |
| **Auth** | **None** (public read) |

#### Query Parameters

| Param | Type | Default | Max | Description |
|-------|------|---------|-----|-------------|
| `limit` | int | 10 | 100 | Max records to return |
| `offset` | int | 0 | — | Skip first N records |

#### Example curl

```bash
curl "https://storage.projectalpha.in/tools/survey_bot?limit=20&offset=0"
```

#### Success Response (200)

```json
[
  {
    "id": 1,
    "created_at": "2026-02-05T10:30:00",
    "user_id": 42,
    "feedback": "Great product!"
  },
  {
    "id": 2,
    "created_at": "2026-02-05T10:31:00",
    "user_id": 43,
    "feedback": "Could be better"
  }
]
```

#### Failure Responses

| Condition | Status | Body |
|-----------|--------|------|
| Tool not found | 404 | `{"detail": "Tool not found"}` |

#### Edge Cases

- **Empty table**: Returns `[]` (empty array), not error
- **Limit > 100**: Capped to 100 by FastAPI validation

---

### 4.4 Delete Tool

**Purpose**: Remove tool registration and drop its table. **IRREVERSIBLE.**

| Property | Value |
|----------|-------|
| **Method** | `DELETE` |
| **URL** | `/tools/{tool_id}` |
| **Auth** | `admin-token` header required |

#### Headers

```
admin-token: admin-secret-123
```

#### Example curl

```bash
curl -X DELETE "https://storage.projectalpha.in/tools/survey_bot" \
  -H "admin-token: admin-secret-123"
```

#### Success Response (200)

```json
{"message": "Tool 'survey_bot' deleted"}
```

#### Failure Responses

| Condition | Status | Body |
|-----------|--------|------|
| Tool not found | 404 | `{"detail": "Tool not found"}` |
| Wrong admin token | 403 | `{"detail": "Forbidden: Admin access only"}` |

#### Edge Cases

- Table drop failure is silently ignored; registry entry is still deleted

---

### 4.5 Common Storage (Legacy)

**Purpose**: Store JSON in shared `multiple_tools` table without schema validation.

| Property | Value |
|----------|-------|
| **Method** | `POST` |
| **URL** | `/common` |
| **Auth** | Required only if `sensitive: 1` |

#### Headers

| Header | Type | Required | Description |
|--------|------|----------|-------------|
| `tool-name` | string | **Yes** | Identifier for the sending tool |
| `sensitive` | int | No | `0` (default) or `1` |
| `token` | string | Conditional | Required if `sensitive=1` |

#### Request Body

Any JSON payload.

#### Example curl (Public)

```bash
curl -X POST "https://storage.projectalpha.in/common" \
  -H "Content-Type: application/json" \
  -H "tool-name: metrics_collector" \
  -H "sensitive: 0" \
  -d '{"cpu": 45, "memory": 2048}'
```

#### Example curl (Sensitive)

```bash
curl -X POST "https://storage.projectalpha.in/common" \
  -H "Content-Type: application/json" \
  -H "tool-name: reports_tool" \
  -H "sensitive: 1" \
  -H "token: token123" \
  -d '{"secret_data": "xyz"}'
```

#### Success Response (200)

```json
{"message": "JSON stored in common table"}
```

#### Failure Responses

| Condition | Status | Body |
|-----------|--------|------|
| Missing token for sensitive | 401 | `{"detail": "Unauthorized: invalid or missing token"}` |
| Invalid token | 401 | `{"detail": "Unauthorized: invalid or missing token"}` |

---

## SECTION 5 — DATA FLOW EXAMPLES

### Example 1: Full Tool Lifecycle

```bash
# Step 1: Register tool
curl -X POST "https://storage.projectalpha.in/register-tool" \
  -H "Content-Type: application/json" \
  -H "admin-token: admin-secret-123" \
  -d '{
    "tool_name": "feedback_bot",
    "token": "fb-token-secret",
    "schema": [
      {"name": "user_id", "type": "int"},
      {"name": "message", "type": "str"}
    ]
  }'
# Response: {"message": "Tool 'feedback_bot' registered and table created"}

# Step 2: Insert data
curl -X POST "https://storage.projectalpha.in/tools/feedback_bot" \
  -H "Content-Type: application/json" \
  -H "token: fb-token-secret" \
  -d '{"user_id": 101, "message": "Love this app!"}'
# Response: {"message": "Data stored successfully"}

# Step 3: Fetch data
curl "https://storage.projectalpha.in/tools/feedback_bot?limit=10"
# Response: [{"id": 1, "created_at": "...", "user_id": 101, "message": "Love this app!"}]

# Step 4: Delete tool (cleanup)
curl -X DELETE "https://storage.projectalpha.in/tools/feedback_bot" \
  -H "admin-token: admin-secret-123"
# Response: {"message": "Tool 'feedback_bot' deleted"}
```

### Example 2: Template Storage Tool

```bash
# Register template storage tool
curl -X POST "https://storage.projectalpha.in/register-tool" \
  -H "Content-Type: application/json" \
  -H "admin-token: admin-secret-123" \
  -d '{
    "tool_name": "report_templates",
    "token": "report-template-access-001",
    "schema": [
      {"name": "code", "type": "str"},
      {"name": "name", "type": "str"},
      {"name": "structure", "type": "json"}
    ]
  }'

# Insert a template
curl -X POST "https://storage.projectalpha.in/tools/report_templates" \
  -H "Content-Type: application/json" \
  -H "token: report-template-access-001" \
  -d '{
    "code": "LAB001",
    "name": "Physics Lab Report",
    "structure": {"sections": [{"title": "Introduction"}, {"title": "Results"}]}
  }'

# Fetch all templates
curl "https://storage.projectalpha.in/tools/report_templates?limit=50"
```

---

## SECTION 6 — FAILURE SCENARIOS

### Scenario: Tool Not Registered

**Request**: `POST /tools/nonexistent_tool`

**Response**: 
```json
{"detail": "Tool not found"}
```
**Status**: 404

---

### Scenario: Wrong Tool Token

**Request**: `POST /tools/survey_bot` with `token: wrong-token`

**Response**:
```json
{"detail": "Unauthorized: Invalid token for this tool"}
```
**Status**: 401

---

### Scenario: Schema Type Mismatch

**Request**: `POST /tools/survey_bot` with `{"user_id": "not-a-number"}`

**Response**:
```json
{"detail": "Field 'user_id' expected int, got <class 'str'>"}
```
**Status**: 400

---

### Scenario: Invalid JSON Body

**Request**: `POST /tools/survey_bot` with malformed JSON

**Response**:
```json
{"detail": [{"loc": ["body"], "msg": "value is not a valid dict", ...}]}
```
**Status**: 422

---

### Scenario: Empty Table Query

**Request**: `GET /tools/empty_tool`

**Response**:
```json
[]
```
**Status**: 200 (empty array, not error)

---

### Scenario: Database Connection Failure

**Response**:
```json
{"detail": "...connection refused..."}
```
**Status**: 500

---

## SECTION 7 — BEST PRACTICES

### Tool Naming

- Use lowercase with underscores: `survey_bot`, `report_templates`
- Avoid special characters, spaces, hyphens
- Keep names short but descriptive
- Remember: table will be `tool_{name}`

### Schema Design

- Define only fields you need (extra fields are ignored anyway)
- Use `int` for IDs/counts, `str` for text, `json` for nested objects
- Consider future needs before registering (schema cannot be modified)

### Security

- **Never expose admin token** to frontend or public code
- Generate unique tokens per tool (avoid reusing tokens)
- Store tool tokens securely (environment variables, secrets manager)
- Consider rate limiting in production

### Production Deployment

- Use PostgreSQL (not SQLite) for production
- Set `DATABASE_URL` via environment variable
- Move `ADMIN_TOKEN` to environment variable
- Enable logging for insert/delete operations
- Monitor `registered_tools` table as source of truth

---

## SECTION 8 — KNOWN PITFALLS

### ❌ Pitfall 1: Confusing Tool Name with Table Name

**Wrong**: Running SQL `SELECT * FROM survey_bot`  
**Correct**: Run `SELECT * FROM tool_survey_bot`

The API uses `tool_name`, but PostgreSQL table is `tool_{tool_name}`.

---

### ❌ Pitfall 2: Using Wrong Endpoint for Registered Tools

**Wrong**: Storing data via `/common` for a registered tool  
**Correct**: Use `POST /tools/{tool_id}`

The `/common` endpoint does NOT use registered tool schemas.

---

### ❌ Pitfall 3: Missing Token Header

**Symptom**: `422 Unprocessable Entity` with missing header error  
**Fix**: Add `token: your-token` header (not `authorization`)

---

### ❌ Pitfall 4: Type Mismatch on Insert

**Symptom**: `400` with "expected int, got str"  
**Fix**: Ensure JSON types match schema (use `42` not `"42"`)

Note: Only `int`, `str`, `bool` are validated. `float`, `json`, `timestamp` are not checked.

---

### ❌ Pitfall 5: Expecting Error on Empty Table

**Symptom**: Expecting 404 when table is empty  
**Reality**: Returns `[]` with 200 OK

An empty response array means "tool exists but has no data."

---

### ❌ Pitfall 6: Schema Cannot Be Updated

**Symptom**: Wanting to add a new field to existing tool  
**Reality**: Not supported. Must delete and re-register tool (loses data).

**Workaround**: Use `json` type field for flexible nested data.

---

## APPENDIX A — Database Tables

### `multiple_tools` (Common Storage)

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Auto-increment PK |
| tool_name | VARCHAR(50) | Tool identifier |
| data | JSON | Payload |
| sensitive | INTEGER | 0 or 1 |
| created_at | TIMESTAMP | Auto-generated |

### `registered_tools` (Tool Registry)

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Auto-increment PK |
| tool_name | VARCHAR(50) | Unique tool identifier |
| token | VARCHAR(100) | Tool access token |
| schema_definition | JSON | Column definitions |
| created_at | TIMESTAMP | Auto-generated |

### `tool_{tool_name}` (Dynamic Tables)

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Auto-increment PK |
| created_at | TIMESTAMP | Auto-generated |
| *...user-defined columns...* | *per schema* | *per schema* |

---

## APPENDIX B — Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | **Yes** | PostgreSQL connection string |

Example:
```
DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/projectalpha_db
```

---

## APPENDIX C — Dependencies

```
fastapi
uvicorn
sqlalchemy
psycopg2-binary
python-dotenv
httpx
```

---

*End of Documentation*
