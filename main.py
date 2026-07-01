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

        payload = {
            "messages": history
        }

        response = httpx.post(url, headers=headers, json=payload, timeout=30)
        data = response.json()

        # Tampilkan response mentah untuk debug
        return {"jawaban": f"DEBUG RESPONSE: {data}"}

    except Exception as e:
        return {"jawaban": f"DEBUG ERROR: {str(e)}"}
