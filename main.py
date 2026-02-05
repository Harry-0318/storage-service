from fastapi import FastAPI, HTTPException, Header, Depends, Body
from sqlalchemy import insert, Table, Column, JSON, Integer, TIMESTAMP, MetaData, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import ProgrammingError
from database import get_db, engine
from models import Base, MultipleTools
from auth import authenticate

# Create tables
Base.metadata.create_all(bind=engine)

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

metadata = MetaData()

@app.post("/tool-{tool_id}")
def store_tool_json(
    tool_id: str,
    payload: dict = Body(...),
    db: Session = Depends(get_db)
):
    # Define tool-specific table
    table_name = f"tool_{tool_id}"
    tool_table = Table(
        table_name,
        metadata,
        Column("id", Integer, primary_key=True, index=True),
        Column("data", JSON, nullable=False),
        Column("created_at", TIMESTAMP, server_default=func.now()),
        extend_existing=True
    )

    # Create table in DB if it doesn't exist
    try:
        tool_table.create(bind=engine, checkfirst=True)
    except ProgrammingError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Insert payload
    stmt = tool_table.insert().values(data=payload)
    db.execute(stmt)
    db.commit()
    return {"message": f"JSON stored in {table_name}"}
