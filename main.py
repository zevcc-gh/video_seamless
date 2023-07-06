import asyncio
import uvicorn
import json

from typing import List, Dict
from pydantic import BaseModel
from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.websockets import WebSocketDisconnect

app = FastAPI()

# Allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the frontend files
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# Mock video queue
idle_video_queue = ["https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4"]
video_queue = [
    "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4",
    "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerMeltdowns.mp4",
]

class Video(BaseModel):
    video_link: str
    user_id: str

# Create a new websocket manager to handle multiple connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    async def disconnect(self, user_id: str):
        del self.active_connections[user_id]

    async def send_message(self, message: str, user_id: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(message)

    async def receive_message(self, user_id: str):
        if user_id in self.active_connections:
            return await self.active_connections[user_id].receive_text()


manager = ConnectionManager()

@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/idle")
def get_idle_video():
    return {"video_link": idle_video_queue[0]}


@app.get("/video")
async def get_video():
    try:
        return {"message": f"{video_queue}"}
    except Exception as e:
        return {"Error": f"{e}"}
        
@app.post("/add-video")
async def add_video(video: Video):
    video_queue.insert(0, video.video_link)  # Add the new video to the front of the queue
    await manager.send_message(json.dumps({"video_link": video.video_link}), video.user_id)
    return {"message": "Video added successfully"}

async def push_queue(websocket):
    while True:
        try:
            # Get the next video link from the queue
            next_link = video_queue.pop(0)
            video_queue.append(next_link)

            # Send the video link to the WebSocket client
            await websocket.send_json({"video_link": next_link})

            await asyncio.sleep(40)  # Wait for 40 secs
        except WebSocketDisconnect:
            break


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    try:
        while True:
            # Wait for a message from the client
            data = await manager.receive_message(user_id)
            
            # Update the video queue with the received data
            video_queue = json.loads(data)
            print(f'Updated video queue for user {user_id}:', video_queue)

            # await push_queue(websocket)
    finally:
        await manager.disconnect(user_id)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)