import os
import subprocess
from datetime import datetime
from typing import List, Optional, Dict

from fastapi import FastAPI, Header, HTTPException, BackgroundTasks
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

if not os.path.exists(LOG_DIR):
    os.mkdir(LOG_DIR)


def load_config(filename: str = None):
    global config
    with open(filename or 'config.json') as f:
        config = TypeAdapter(Dict[str, Config]).validate_json(f.read())


load_config()


def execute_command(name: str, command: str, cwd: Optional[str], parameters: Optional[List[str]] = None):
    timestamp: str = datetime.now().strftime("%Y%m%d%H%M%S")
    args: List[str] = [command] + (parameters or [])
    with open(os.path.join(LOG_DIR, f"{name}-{timestamp}.log"), "a") as log_file:
        return subprocess.run(
            args, shell=False, stdout=log_file, stderr=log_file, cwd=cwd, text=True)


@app.post("/api/webhook")
async def execute_script(webhook_request: WebhookRequest, background_tasks: BackgroundTasks,
                         authorization: str = Header(default=None)) -> Dict[str, int]:
    if (c := config.get(webhook_request.name, None)) is None or authorization != c.secret:
        raise HTTPException(status_code=401, detail="Unauthorized")

    background_tasks.add_task(execute_command, webhook_request.name, c.command, c.cwd, webhook_request.parameters)

    return {"code": 200}


@app.get("/api/health")
async def healthcheck():
    return {"status": 200}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), workers=4)
