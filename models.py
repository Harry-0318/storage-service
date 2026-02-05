from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, JSON, TIMESTAMP, func

Base = declarative_base()

class MultipleTools(Base):
    __tablename__ = "multiple_tools"

    id = Column(Integer, primary_key=True, index=True)
    tool_name = Column(String(50), nullable=False)       # which tool sent the JSON
    data = Column(JSON, nullable=False)                  # JSON payload
    sensitive = Column(Integer, default=0)               # 0 = public, 1 = sensitive
    created_at = Column(TIMESTAMP, server_default=func.now())
