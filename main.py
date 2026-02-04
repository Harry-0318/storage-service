from fastapi import FastAPI
from database import engine

app = FastAPI()

@app.get("/")
def health_check():
    # try touching the DB
    conn = engine.connect()
    conn.close()
    return {"status": "storage service + db connected"}
