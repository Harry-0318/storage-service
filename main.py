from fastapi import FastAPI, HTTPException, Header, Depends, Body, Query
from sqlalchemy import insert, select, text, Table
from sqlalchemy.orm import Session
from sqlalchemy.exc import ProgrammingError, IntegrityError, NoSuchTableError
from database import get_db, engine
from models import Base, MultipleTools, RegisteredTool
from auth import authenticate, verify_admin
from tool_registry import validate_schema, validate_payload, create_tool_table
from sqlalchemy import MetaData


# Create tables
Base.metadata.create_all(bind=engine)
metadata = MetaData()

app = FastAPI(title="ProjectAlpha JSON Storage Service")

@app.post("/common")
def store_common_json(
    tool_name: str = Header(...),
    sensitive: int = Header(default=0),
    token: str = Header(default=None),  # token header, optional
    payload: dict = Body(...),
    db: Session = Depends(get_db)
):
    # Check authentication if sensitive
    if sensitive == 1:
        if not token or not authenticate(token):
            raise HTTPException(status_code=401, detail="Unauthorized: invalid or missing token")

    # Insert into multiple_tools table
    stmt = insert(MultipleTools).values(
        tool_name=tool_name,
        data=payload,
        sensitive=sensitive
    )
    db.execute(stmt)
    db.commit()
    return {"message": "JSON stored in common table"}


# --- New Tool Registration Framework ---

@app.post("/register-tool")
def register_tool(
    tool_name: str = Body(...),
    token: str = Body(...),
    schema: list = Body(...),
    admin_token: str = Header(..., alias="admin-token"),
    db: Session = Depends(get_db)
):
    """
    Registers a new tool and creates its specific table.
    Requires 'admin-token' header.
    Schema example: [{"name": "age", "type": "int"}, {"name": "bio", "type": "str"}]
    """
    if not verify_admin(admin_token):
        raise HTTPException(status_code=403, detail="Forbidden: Admin access only")

    # Validate Schema
    try:
        validate_schema(schema)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Check if tool already exists
    existing_tool = db.query(RegisteredTool).filter(RegisteredTool.tool_name == tool_name).first()
    if existing_tool:
        raise HTTPException(status_code=400, detail=f"Tool '{tool_name}' already registered")

    # Register in DB
    new_tool = RegisteredTool(
        tool_name=tool_name,
        token=token,
        schema_definition=schema
    )
    db.add(new_tool)
    
    # Create Table
    tool_table = create_tool_table(tool_name, schema, metadata)
    try:
        tool_table.create(bind=engine, checkfirst=True)
        db.commit() # Commit transaction only after table creation success
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create table: {str(e)}")

    return {"message": f"Tool '{tool_name}' registered and table created"}


@app.post("/tools/{tool_id}")
def store_tool_data(
    tool_id: str,
    token: str = Header(...),
    payload: dict = Body(...),
    db: Session = Depends(get_db)
):
    """
    Store data for a registered tool.
    Validates token against the registered tool's token.
    Validates payload against schema.
    """
    # Find tool
    tool_record = db.query(RegisteredTool).filter(RegisteredTool.tool_name == tool_id).first()
    if not tool_record:
        raise HTTPException(status_code=404, detail="Tool not found")

    # Validate Auth
    if tool_record.token != token:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid token for this tool")

    # Validate Payload
    try:
        validate_payload(payload, tool_record.schema_definition)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Insert Data
    tool_table = create_tool_table(tool_id, tool_record.schema_definition, metadata)
    
    # Safe insert: filter payload keys to match columns only (or rely on SQLAlchemy to error/ignore)
    # SQLAlchemy insert will error on unknown columns if not careful.
    # We should only pass keys that are in the schema (or valid columns like id, created_at - but those are auto).
    
    valid_keys = [f["name"] for f in tool_record.schema_definition]
    clean_payload = {k: v for k, v in payload.items() if k in valid_keys}
    
    try:
        stmt = tool_table.insert().values(**clean_payload)
        db.execute(stmt)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "Data stored successfully"}


@app.get("/tools/{tool_id}")
def get_tool_data(
    tool_id: str,
    limit: int = Query(10, le=100),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    """
    Retrieve data for a tool. Use limit/offset for pagination.
    """
    tool_record = db.query(RegisteredTool).filter(RegisteredTool.tool_name == tool_id).first()
    if not tool_record:
        raise HTTPException(status_code=404, detail="Tool not found")

    tool_table = create_tool_table(tool_id, tool_record.schema_definition, metadata)
    
    stmt = select(tool_table).limit(limit).offset(offset)
    result = db.execute(stmt)
    rows = result.mappings().all()
    
    return rows


@app.delete("/tools/{tool_id}")
def delete_tool(
    tool_id: str,
    admin_token: str = Header(..., alias="admin-token"),
    db: Session = Depends(get_db)
):
    """
    Delete a tool and its table. Requires Admin Token.
    """
    if not verify_admin(admin_token):
        raise HTTPException(status_code=403, detail="Forbidden: Admin access only")

    tool_record = db.query(RegisteredTool).filter(RegisteredTool.tool_name == tool_id).first()
    if not tool_record:
        raise HTTPException(status_code=404, detail="Tool not found")

    # Drop Table
    tool_table = create_tool_table(tool_id, tool_record.schema_definition, metadata)
    try:
        tool_table.drop(bind=engine, checkfirst=True)
    except Exception as e:
        # Continue to delete record even if table drop fails (or maybe raise?)
        # Better to raise/log, but let's try to be clean.
        pass

    # remove from registry
    db.delete(tool_record)
    db.commit()

    return {"message": f"Tool '{tool_id}' deleted"}
