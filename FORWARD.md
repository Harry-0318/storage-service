
# **ProjectAlpha — Tool-Specific Tables Roadmap**

### **Current State**

1. **Shared table**: `multiple_tools`

   * Stores JSON from all small tools.
   * Optional token authentication if `sensitive=1`.
2. **FastAPI endpoints**:

   * `/common` → shared table
   * `/tool-id` → currently optional, planned for tool-specific tables
3. **Authentication**: token-based (`auth.py`)
4. **Database**: PostgreSQL on `projectalpha-vm`
5. **Hosting**: `storage.projectalpha.in` behind Caddy

---

### **Goal**

* Move larger tools or tools requiring isolation to **their own table**.
* Keep `/common` for **small tools / low-sensitivity data**.
* Maintain **centralized authentication**.

---

## **Step 1 — Decide Criteria for Tool-Specific Table**

Currently, we don’t check JSON size; so you’ll need rules like:

1. Any **tool that grows beyond a few KB** → dedicated table.
2. **Sensitive tools** → dedicated table if you want stricter access control.
3. Otherwise, small, public, or low-sensitivity tools stay in `/common`.

**Action**: Make a small configuration dict in Python:

```python
# tool_config.py
TOOL_CONFIG = {
    "reports": {"sensitive": 1, "use_individual_table": True},
    "analytics": {"sensitive": 1, "use_individual_table": True},
    "metrics": {"sensitive": 0, "use_individual_table": False},  # stays in /common
}
```

---

## **Step 2 — Map `/tool-id` endpoint to dynamic tables**

* Each tool gets a table named `tool_<tool_id>`:

| Tool ID   | Table Name              | JSON storage type |
| --------- | ----------------------- | ----------------- |
| reports   | tool_reports            | JSON              |
| analytics | tool_analytics          | JSON              |
| metrics   | stays in multiple_tools | JSON              |

* Use **SQLAlchemy dynamic table creation**:

```python
from sqlalchemy import Table, Column, JSON, Integer, TIMESTAMP, MetaData, func

metadata = MetaData()

def get_tool_table(tool_id: str):
    table_name = f"tool_{tool_id}"
    return Table(
        table_name,
        metadata,
        Column("id", Integer, primary_key=True),
        Column("data", JSON),
        Column("created_at", TIMESTAMP, server_default=func.now()),
        extend_existing=True
    )
```

* This is **exactly how `/tool-id` will store JSON for tool-specific tables**.

---

## **Step 3 — Authentication**

* `/common`: only checks token if `sensitive=1`.
* `/tool-id`: optionally enforce token **per tool** using `TOOL_CONFIG`.

Example:

```python
config = TOOL_CONFIG.get(tool_id)
if config and config["sensitive"] == 1:
    if not token or not authenticate(token):
        raise HTTPException(status_code=401, detail="Unauthorized")
```

* Ensures **each tool-specific table can be protected individually**.

---

## **Step 4 — Migration Path**

1. **Keep `/common` live** for all current small tools.
2. **For a new tool** or growing tool:

   * Add entry in `TOOL_CONFIG` → `use_individual_table=True`.
   * `/tool-id` endpoint auto-creates its table.
3. **Optional migration of old data** from `/common` → tool-specific table if desired:

```python
# Example migration
db.execute("INSERT INTO tool_reports(data) SELECT data FROM multiple_tools WHERE tool_name='reports'")
db.commit()
```

4. **Update tool** to call `/tool-reports` instead of `/common`.

---

## **Step 5 — Centralized Documentation**

For each tool:

| Tool Name | Endpoint          | Table          | Sensitive | Token    |
| --------- | ----------------- | -------------- | --------- | -------- |
| metrics   | `/common`         | multiple_tools | 0         | None     |
| reports   | `/tool-reports`   | tool_reports   | 1         | token123 |
| analytics | `/tool-analytics` | tool_analytics | 1         | token456 |

* This keeps **centralized visibility** and avoids tools accessing each other’s data.

---

## **Step 6 — Things to Know Moving Forward**

1. **Naming convention**: Always `tool_<tool_id>` to avoid collisions.
2. **Dynamic table creation** is safe with `checkfirst=True`.
3. **Sensitive tools** → enforce token per tool; public tools can stay in `/common`.
4. **Schema consistency**: All tool-specific tables use the same columns: `id`, `data`, `created_at`.
5. **Monitoring / metrics**: Log which tool posts to which table for debugging.

---

✅ **Summary for ProjectAlpha**

1. **Keep `/common`** for all small/public tools.
2. **Use `/tool-id`** for large or sensitive tools.
3. **Tool-specific tables** are auto-created dynamically.
4. **Authentication** can be enforced per tool using `TOOL_CONFIG`.
5. **Centralized documentation** allows developers to know which endpoint and token to use.
