from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import sqlite3
import httpx
import time

app = FastAPI()

CLOUDFLARE_ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
CLOUDFLARE_API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN")
CLOUDFLARE_MODEL = "@cf/zai-org/glm-5.2"

DB_PATH = "chat_history.db"

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
    try:
        history = get_history(request.session_id)
        history.append({"role": "user", "content": request.pesan})
        save_message(request.session_id, "user", request.pesan)

        url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{CLOUDFLARE_MODEL}"

        headers = {
            "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
            "Content-Type": "application/json"
        }

        payload = {"messages": history}

        for attempt in range(3):
            response = httpx.post(url, headers=headers, json=payload, timeout=30)
            data = response.json()

            if data.get("success") and data.get("result"):
                result = data["result"]

                # Format OpenAI-style (choices)
                if "choices" in result and len(result["choices"]) > 0:
                    jawaban = result["choices"][0]["message"]["content"]
                # Format Cloudflare biasa (response)
                elif "response" in result:
                    jawaban = result["response"]
                else:
                    return {"jawaban": f"Format response tidak dikenali: {result}"}

                save_message(request.session_id, "assistant", jawaban)
                return {"jawaban": jawaban}

            if any(e.get("code") == 3040 for e in data.get("errors", [])):
                if attempt < 2:
                    time.sleep(2)
                    continue
                else:
                    return {"jawaban": "Server AI sedang sibuk, coba lagi dalam beberapa detik ya."}

            return {"jawaban": f"Error dari Cloudflare: {data.get('errors')}"}

    except Exception as e:
        return {"jawaban": f"DEBUG ERROR: {str(e)}"}


@app.post("/reset")
def reset(request: ResetRequest):
    delete_history(request.session_id)
    return {"status": "History berhasil direset"}


app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return FileResponse("static/index.html")
