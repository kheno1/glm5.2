from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from zhipuai import ZhipuAI
import os
import sqlite3

app = FastAPI()
client = ZhipuAI(api_key=os.environ.get("ZHIPU_API_KEY"))

DB_PATH = "chat_history.db"

# Inisialisasi database
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

def get_history(session_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM history WHERE session_id = ? ORDER BY id ASC",
        (session_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"role": row[0], "content": row[1]} for row in rows]

def save_message(session_id: str, role: str, content: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO history (session_id, role, content) VALUES (?, ?, ?)",
        (session_id, role, content)
    )
    conn.commit()
    conn.close()

def delete_history(session_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM history WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()


class ChatRequest(BaseModel):
    pesan: str
    session_id: str = "default"

class ResetRequest(BaseModel):
    session_id: str = "default"


@app.post("/chat")
def chat(request: ChatRequest):
    # Ambil history dari database
    history = get_history(request.session_id)

    # Tambahkan pesan user ke history
    history.append({"role": "user", "content": request.pesan})
    save_message(request.session_id, "user", request.pesan)

    # Kirim ke GLM
    response = client.chat.completions.create(
        model="glm-4",
        messages=history
    )

    jawaban = response.choices[0].message.content

    # Simpan jawaban GLM ke database
    save_message(request.session_id, "assistant", jawaban)

    return {"jawaban": jawaban}


@app.post("/reset")
def reset(request: ResetRequest):
    delete_history(request.session_id)
    return {"status": "History berhasil direset"}


app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return FileResponse("static/index.html")
