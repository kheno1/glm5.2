from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from zhipuai import ZhipuAI
import os

app = FastAPI()
client = ZhipuAI(api_key=os.environ.get("ZHIPU_API_KEY"))

# Simpan history per sesi sederhana (in-memory)
chat_history = []

class ChatRequest(BaseModel):
    pesan: str

@app.post("/chat")
def chat(request: ChatRequest):
    # Tambahkan pesan user ke history
    chat_history.append({
        "role": "user",
        "content": request.pesan
    })

    # Kirim seluruh history ke GLM
    response = client.chat.completions.create(
        model="glm-4",
        messages=chat_history
    )

    jawaban = response.choices[0].message.content

    # Tambahkan jawaban GLM ke history
    chat_history.append({
        "role": "assistant",
        "content": jawaban
    })

    return {"jawaban": jawaban}

@app.post("/reset")
def reset():
    chat_history.clear()
    return {"status": "History berhasil direset"}

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return FileResponse("static/index.html")
