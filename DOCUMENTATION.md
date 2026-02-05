# **ProjectAlpha Storage Service — Common Table Documentation**

### **Overview**

The `/common` endpoint stores **JSON data from multiple tools** in a **shared PostgreSQL table** called `multiple_tools`.

* **Small tools** or **low-sensitivity data** use this shared table.
* **Sensitive data** can optionally require a **token** for authentication.

---

## **Database Setup**

1. Ensure your PostgreSQL database exists:

```sql
CREATE DATABASE projectalpha_db;
CREATE USER alphauser WITH PASSWORD 'StrongPassword123!';
GRANT ALL PRIVILEGES ON DATABASE projectalpha_db TO alphauser;
```

2. Environment file `.env` (in project folder):

```
DATABASE_URL=postgresql+psycopg2://alphauser:StrongPassword123!@localhost:5432/projectalpha_db
```

3. Database models (`models.py`):

```python
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, JSON, TIMESTAMP, func

Base = declarative_base()

class MultipleTools(Base):
    __tablename__ = "multiple_tools"

    id = Column(Integer, primary_key=True, index=True)
    tool_name = Column(String(50), nullable=False)
    data = Column(JSON, nullable=False)
    sensitive = Column(Integer, default=0)  # 0=public, 1=sensitive
    created_at = Column(TIMESTAMP, server_default=func.now())
```

4. Create the table in the database:

```python
from database import engine
from models import Base

Base.metadata.create_all(bind=engine)
print("Tables created successfully!")
```

---

## **API Endpoint**

### **POST /common**

* **URL**: `https://storage.projectalpha.in/common`
* **Method**: `POST`
* **Purpose**: Store JSON data from multiple tools in the shared table.

---

### **Headers**

| Header      | Type | Required? | Description                                     |
| ----------- | ---- | --------- | ----------------------------------------------- |
| `tool-name` | str  | Yes       | Name of the tool sending the JSON               |
| `sensitive` | int  | No        | 0 = public, 1 = sensitive (requires token if 1) |
| `token`     | str  | Cond.     | Required only if `sensitive=1`                  |

---

### **Request Body**

* JSON format (any JSON payload your tool needs to store).
* Example:

```json
{
  "report_date": "2026-02-05",
  "total_users": 123,
  "notes": "All systems operational"
}
```

---

### **Behavior**

1. **sensitive=0** → stores JSON in `multiple_tools` table, no authentication needed.
2. **sensitive=1** → must provide valid `token` header (from `auth.py`) or request is rejected with **401 Unauthorized**.

---

### **Response**

* **Success (201/200)**

```json
{
  "message": "JSON stored in common table"
}
```

* **Unauthorized (401)**

```json
{
  "detail": "Unauthorized: invalid or missing token"
}
```

---

### **Example curl Requests**

#### 1. Public data (no token needed)

```bash
curl -X POST "https://storage.projectalpha.in/common" \
-H "tool-name: test_tool" \
-H "sensitive: 0" \
-H "Content-Type: application/json" \
-d '{"example": "public data"}'
```

#### 2. Sensitive data (token required)

```bash
curl -X POST "https://storage.projectalpha.in/common" \
-H "tool-name: reports_tool" \
-H "sensitive: 1" \
-H "token: token123" \
-H "Content-Type: application/json" \
-d '{"example": "private data"}'
```

---

### **Database Table Usage**

* Table: `multiple_tools`
* Columns:

| Column       | Type      | Description                |
| ------------ | --------- | -------------------------- |
| `id`         | int       | Auto-increment primary key |
| `tool_name`  | varchar   | Tool sending the data      |
| `data`       | JSON      | JSON payload from tool     |
| `sensitive`  | int       | 0=public, 1=sensitive      |
| `created_at` | timestamp | Automatic timestamp        |

* Example SQL query:

```sql
SELECT * FROM multiple_tools WHERE tool_name='reports_tool';
```

---
