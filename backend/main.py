import os
import shutil
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base, Dialog, Message
from pydantic import BaseModel
import uuid
from fastapi.staticfiles import StaticFiles

DATABASE_URL = "sqlite:///./chat.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


class DialogConnection:
    def __init__(self, ws: WebSocket, name: str, dialog_code: str):
        self.ws = ws
        self.name = name
        self.dialog_code = dialog_code


class ConnectionManager:
    def __init__(self):
        self.dialogs: dict[str, list[DialogConnection]] = {}

    async def join(self, ws: WebSocket, dialog_code: str, name: str):
        await ws.accept()
        conn = DialogConnection(ws, name, dialog_code)
        if dialog_code not in self.dialogs:
            self.dialogs[dialog_code] = []
        self.dialogs[dialog_code].append(conn)
        return conn

    def leave(self, conn: DialogConnection):
        if conn.dialog_code in self.dialogs:
            self.dialogs[conn.dialog_code] = [
                c for c in self.dialogs[conn.dialog_code] if c.ws != conn.ws
            ]
            if not self.dialogs[conn.dialog_code]:
                del self.dialogs[conn.dialog_code]

    async def send_to_dialog(self, dialog_code: str, message: dict):
        if dialog_code in self.dialogs:
            for conn in self.dialogs[dialog_code]:
                try:
                    await conn.ws.send_json(message)
                except:
                    pass


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    conn = None
    try:
        await websocket.accept()
        while True:
            raw = await websocket.receive_text()
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
                
            action = data.get("action")
            
            if action == "join":
                dialog_code = data.get("dialog_code", "").upper()
                name = data.get("name", "Anon")
                conn = DialogConnection(websocket, name, dialog_code)
                
                if dialog_code not in manager.dialogs:
                    manager.dialogs[dialog_code] = []
                manager.dialogs[dialog_code].append(conn)
                
                db = SessionLocal()
                existing = db.query(Dialog).filter(Dialog.code == dialog_code).first()
                if not existing:
                    new_dialog = Dialog(code=dialog_code)
                    db.add(new_dialog)
                    db.commit()
                db.close()
                
            elif action == "message" and conn:
                text = data.get("text", "")
                sender = conn.name
                dialog_code = conn.dialog_code
                
                db = SessionLocal()
                msg = Message(dialog_code=dialog_code, sender=sender, text=text)
                db.add(msg)
                db.commit()
                db.close()
                
                if dialog_code in manager.dialogs:
                    for c in manager.dialogs[dialog_code]:
                        try:
                            await c.ws.send_json({"sender": sender, "text": text})
                        except:
                            pass
                
    except WebSocketDisconnect:
        if conn:
            if conn.dialog_code in manager.dialogs:
                manager.dialogs[conn.dialog_code] = [c for c in manager.dialogs[conn.dialog_code] if c.ws != websocket]
    except Exception as e:
        print(f"WS error: {e}")
        if conn and conn.dialog_code in manager.dialogs:
            manager.dialogs[conn.dialog_code] = [c for c in manager.dialogs.get(conn.dialog_code, []) if c.ws != websocket]


@app.get("/dialog/{code}")
async def get_dialog(code: str):
    db = SessionLocal()
    dialog = db.query(Dialog).filter(Dialog.code == code.upper()).first()
    messages = db.query(Message).filter(Message.dialog_code == code.upper()).all()
    result = {
        "dialog": {"code": dialog.code, "created_at": dialog.created_at.isoformat()} if dialog else None,
        "messages": [{"sender": m.sender, "text": m.text, "time": m.timestamp.isoformat()} for m in messages]
    }
    db.close()
    return result


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_extension = file.filename.split(".")[-1] if file.filename else "bin"
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return {"file_path": unique_filename}