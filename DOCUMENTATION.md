
# **ProjectAlpha Storage Service — Documentation**

### **Overview**

This service provides JSON storage for multiple tools. It supports two modes:
1. **Common Table**: Shared storage for small tools (`/common` endpoint).
2. **Tool-Specific Tables**: Dedicated, dynamically created tables for registered tools (`/tools/{tool_id}` endpoint).

---

## **1. Common Storage (Legacy/Simple)**

### **POST /common**
Stores JSON in a shared `multiple_tools` table.
- **Headers**: `tool-name`, `sensitive` (0/1), `token` (if sensitive).
- **Body**: Any JSON.

---

## **2. Tool Registration & Dedicated Tables (New)**

For tools that need their own table or specific schema validation.

### **Authentication**
- **Admin Token**: Required for registering or deleting tools. (Default: `admin-secret-123`)
- **Tool Token**: Assigned during registration, required for posting data.

### **Endpoints**

#### **A. Register a New Tool**
**POST** `/register-tool`

Creates a dedicated table `tool_{tool_name}` and registers the schema.

**Headers:**
- `admin-token`: `<ADMIN_TOKEN>`

**Body:**
```json
{
  "tool_name": "survey_bot",
  "token": "secure-tool-token-123",
  "schema": [
    {"name": "user_id", "type": "int"},
    {"name": "feedback", "type": "str"}
  ]
}
```

**Supported Types:** `int`, `str`, `bool`, `json`, `float`, `timestamp`.

---

#### **B. Store Data**
**POST** `/tools/{tool_id}`

Stores data into the tool's specific table. Validates payload against the registered schema.

**Headers:**
- `token`: `<TOOL_TOKEN>`

**Body:**
```json
{
  "user_id": 42,
  "feedback": "Loving the new feature!"
}
```

---

#### **C. Retrieve Data**
**GET** `/tools/{tool_id}?limit=10&offset=0`

Fetches data from the tool's table.

**Query Params:**
- `limit`: Max records (default 10).
- `offset`: Pagination offset (default 0).

---

#### **D. Delete Tool**
**DELETE** `/tools/{tool_id}`

Drop the tool's table and remove registration. **Irreversible.**

**Headers:**
- `admin-token`: `<ADMIN_TOKEN>`

---

## **3. Setup & Configuration**

### **Environment Variables**
- `DATABASE_URL`: Connection string (PostgreSQL recommended, SQLite supported for testing).
- `ADMIN_TOKEN`: Set in `auth.py` (Current default: `admin-secret-123`).

### **Tool Registry**
The system maintains a `registered_tools` table to track:
- Tool Name
- Access Token
- Schema Definition (JSON)

This allows the API to dynamically load the correct table schema for validation and storage.
