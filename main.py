import os
import subprocess
from datetime import datetime
from typing import List, Optional, Dict

from fastapi import FastAPI, Header, HTTPException, BackgroundTasks, Response
import shelve
from pydantic import BaseModel, Field, TypeAdapter


class Config(BaseModel):
    command: str = Field(description="Script filepath")
    secret: str = Field(description="Secret token")
    cwd: Optional[str] = Field(description="Working directory", default=None)


class WebhookRequest(BaseModel):
    name: str = Field(description="Script name")
    parameters: Optional[List[str]] = Field(description="Script parameters", default_factory=list)


app = FastAPI()
LOG_DIR = "logs"
config: Dict[str, Config] = ...
SHELVE_FILE_NAME: str = "tasks"

if not os.path.exists(LOG_DIR):
    os.mkdir(LOG_DIR)


def load_config(filename: str = None):
    global config
    with open(filename or 'config.json') as f:
        config = TypeAdapter(Dict[str, Config]).validate_json(f.read())


load_config()


def execute_command(name: str, command: str, cwd: Optional[str], parameters: Optional[List[str]] = None) -> None:
    with shelve.open(SHELVE_FILE_NAME) as tasks:
        tasks[name] = -1
    timestamp: str = datetime.now().strftime("%Y%m%d%H%M%S")
    cmd: str = ' '.join([command] + (parameters or []))
    with open(os.path.join(LOG_DIR, f"{name}-{timestamp}.log"), "a") as log_file:
        run_result = subprocess.run(cmd, shell=True, stdout=log_file, stderr=log_file, cwd=cwd, text=True)
    with shelve.open(SHELVE_FILE_NAME) as tasks:
        tasks[name] = run_result.returncode


@app.get("/api/status")
def status(name: str, response: Response, authorization: str = Header(default=None)) -> Dict[str, int]:
    if (c := config.get(name, None)) is None:
        raise HTTPException(status_code=404, detail="Not found")
    if authorization != c.secret:
        raise HTTPException(status_code=401, detail="Unauthorized")
    with shelve.open(SHELVE_FILE_NAME) as tasks:
        if name not in tasks:
            raise HTTPException(status_code=404, detail="Task Not found")
        if tasks[name] == -1:
            response.status_code = 202
            return {"code": 202}
        else:
            code: int = tasks.pop(name)
            if code == 0:
                response.status_code = 200
                return {"code": 200}
            else:
                response.status_code = 500
                return {"code": 500}


@app.post("/api/webhook")
async def webhook(webhook_request: WebhookRequest, background_tasks: BackgroundTasks,
                  response: Response, authorization: str = Header(default=None)) -> Dict[str, int]:
    if (c := config.get(webhook_request.name, None)) is None:
        raise HTTPException(status_code=404, detail="Not found")
    if authorization != c.secret:
        raise HTTPException(status_code=401, detail="Unauthorized")
    with shelve.open(SHELVE_FILE_NAME) as tasks:
        if webhook_request.name in tasks:
            raise HTTPException(status_code=409, detail="Already running")

    background_tasks.add_task(execute_command, webhook_request.name, c.command, c.cwd, webhook_request.parameters)
    response.status_code = 201

    return {"code": 201}


@app.get("/api/health")
async def healthcheck():
    return {"status": 200}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), workers=4)
