import asyncio

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import json

from Utils.llm_api import StreamLlmApi, LlmApi

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to your front-end domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/llm/stream")
async def stream_output(request: Request):
    """
    Endpoint to handle streaming output.
    The client sends a JSON payload with a 'message' field.
    """
    body = await request.json()
    msg = body.get("message")

    # Initialize the StreamLlmApi and get the generator
    model = StreamLlmApi()
    stream_generator = model.znxz(msg)

    full_response = ""

    async def event_generator():
        nonlocal full_response  # 声明使用外部作用域的变量
        for chunk in stream_generator:
            full_response += chunk
            yield chunk

    # Use StreamingResponse to stream the output to the client
    return StreamingResponse(event_generator(), media_type="text/plain")


@app.post("/llm")
async def ask_llm(request: Request):
    body = await request.json()
    msg = body.get("message")

    model = LlmApi()
    result = model.znxz(msg)

    return result

if __name__ == "__main__":
    import uvicorn

    # Run the FastAPI app
    uvicorn.run(app, host="127.0.0.1", port=8000)
