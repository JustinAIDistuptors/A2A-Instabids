from fastapi import FastAPI, WebSocket, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from instabids.agents.factory import get_homeowner_agent
from instabids.data_access import create_project, get_project_status
from instabids.webhooks import verify_signature, push_to_ui
import uuid, asyncio

app = FastAPI(title="Instabids A2A Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------- A2A endpoints ------- #
@app.post("/a2a/v1/tasks", status_code=202)
async def create_task(payload: dict, token: str = Depends(verify_signature)):
    task_id = uuid.uuid4().hex
    asyncio.create_task(run_homeowner_flow(task_id, payload))
    return {"task_id": task_id, "status": "IN_PROGRESS"}


@app.get("/a2a/v1/tasks/{task_id}")
async def get_task(task_id: str, token: str = Depends(verify_signature)):
    status = await get_project_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="task not found")
    return status


# ------ WebSocket stream for UI ------ #
@app.websocket("/ws/bids/{task_id}")
async def ws_bids(websocket: WebSocket, task_id: str):
    await websocket.accept()
    async for event in push_to_ui.subscribe(task_id):
        await websocket.send_json(event)


# ------ Internal async workflow ------ #
async def run_homeowner_flow(task_id: str, payload: dict):
    agent = get_homeowner_agent()
    await create_project(task_id, payload)
    await agent.run_async(task_id=task_id, project=payload)
