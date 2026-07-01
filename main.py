from fastapi import FastAPI
from pydantic import BaseModel
from zhipuai import ZhipuAI
import os

app = FastAPI()
client = ZhipuAI(api_key=os.environ.get("ZHIPU_API_KEY"))

class ChatRequest(BaseModel):
    pesan: str

@app.post("/chat")
def chat(request: ChatRequest):
    response = client.chat.completions.create(
        model="glm-4",
        messages=[{"role": "user", "content": request.pesan}]
    )
    return {"jawaban": response.choices[0].message.content}

@app.get("/")
def root():
    return {"status": "GLM API aktif"}
