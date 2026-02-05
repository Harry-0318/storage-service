
# **ProjectAlpha — Roadmap & Forward Looking Notes**

### **Completed Objectives**
- [x] **Shared Storage**: `/common` endpoint for small tools.
- [x] **Dynamic Tool Registration**: `/register-tool` to create tables on the fly.
- [x] **Dedicated Endpoints**: `/tools/{tool_id}` for isolated data storage.
- [x] **Schema Validation**: Basic type checking enforced during data ingestion.

---

## **Future Improvements**

### **1. Enhanced Security**
- **Token Management**: currently tokens are plain strings in `auth.py` or DB. Move to hashed tokens (bcrypt) for `RegisteredTool`.
- **API Keys**: Implement proper API Key generation instead of user-supplied strings.
- **Admin Auth**: Move `ADMIN_TOKEN` to environment variable.

### **2. Advanced Schema features**
- **Migrations**: Allow updating schema (adding columns) for existing tools. currently, schema is fixed at registration.
- **Validation**: Add more complex validation (regex, range checks) in `tool_registry.py`.

### **3. Data Management**
- **Soft Delete**: `DELETE /tools/{tool_id}` currently drops the table. Implement soft-delete (mark as `deleted_at`) to prevent data loss.
- **Archival**: automated logic to move old data to cold storage (e.g. S3) from `tool_reports` etc.

### **4. Metrics & Monitoring**
- Track usage per tool (request count, storage size).
- Expose an endpoint `/admin/stats` to see system health.

---

### **Architecture Notes**
- **Database**: We are using SQLAlchemy dynamic table creation. Ensure `pool_pre_ping=True` is enabled for stability.
- **Scaling**: If tool count grows > 1000s, having individual tables might stress the DB catalog. Consider sharding or using JSONB columns in a partitioned table for medium-scale tools.
