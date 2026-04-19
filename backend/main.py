import os
import shutil
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base, Message  # Относительный импорт для запуска из корня

# Настройки БД
DATABASE_URL = "sqlite:///./chat.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

app = FastAPI()
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            db = SessionLocal()
            new_msg = Message(sender_id=user_id, message_text=data)
            db.add(new_msg)
            db.commit()
            
            await manager.broadcast({"sender_id": user_id, "text": data})
            db.close()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/upload")
async def upload_file(user_id: str, file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"file_path": file_path}
