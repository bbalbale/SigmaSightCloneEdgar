#!/usr/bin/env python3
"""
Windows SSE Test - Minimal FastAPI SSE endpoint for testing
"""
from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import time

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3005", "http://127.0.0.1:3005"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def test_sse_stream():
    """Simple SSE stream for Windows testing"""
    for i in range(5):
        # Standard SSE format
        data = json.dumps({"message": f"Test message {i}", "timestamp": time.time()})
        yield f"data: {data}\n\n"
        await asyncio.sleep(1)
    
    yield f"data: {json.dumps({'message': 'Stream complete', 'done': True})}\n\n"

@app.get("/test-sse")
async def test_sse():
    """Test SSE endpoint for Windows debugging"""
    return StreamingResponse(
        test_sse_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )

@app.get("/health")
async def health():
    return {"status": "healthy", "platform": "windows_test"}

if __name__ == "__main__":
    import uvicorn
    print("Starting Windows SSE Test Server on http://localhost:8001")
    print("Test URL: http://localhost:8001/test-sse")
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")