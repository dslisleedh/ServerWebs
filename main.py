import asyncio
import json
import subprocess as sp
from datetime import datetime, timedelta
from pydantic import BaseModel

import psutil
from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi_utils.tasks import repeat_every


app = FastAPI()
app.logs = {}


class LogBody(BaseModel):
    data: dict


@app.get("/trainlog/reset_logs")
async def reset_logs():
    app.logs = {}
    return 'OK'

# For Debugging
@app.post("/trainlog/stack")
async def stack_log(body: LogBody):
    app.logs = body


@app.post("/trainlog/post_logs")
async def post_log_endpoint(item: LogBody):
    data = dict(item.data)
    name = data.pop('name')
    epoch = data.pop('epoch')
    if name not in app.logs:
        app.logs[name] = []
    app.logs[name].append(
        {
            'epoch': epoch,
            'logs': data,
            'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    )
    return {'message': 'success'}


# @app.on_event('startup')
# @repeat_every(seconds=30)
# async def delete_deprecated_logs():
#     for k, v in app.logs.items():
#         app.logs.pop(k) if len(v) > 0 and (datetime.now() - datetime.strptime(v[-1]['time'], "%Y-%m-%d %H:%M:%S")) > timedelta(minutes=30) else None


@app.get("/trainlog/check_keys")
async def check_keys():
    return list(app.logs.keys())


async def log_tracker(request: Request):
    while True:
        out = json.dumps(app.logs)
        yield f"data:{out}\n\n"
        await asyncio.sleep(2)


@app.get("/trainlog/data")
async def trainlog_data(request: Request):
    response = StreamingResponse(log_tracker(request), media_type="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response


@app.get("/trainlog", response_class=FileResponse)
def logs():
    return "pages/trainlog.html"


# ---------------------------------- resource tracker ----------------------------------


async def resource_tracker(request: Request):
    def get_gpu_percentage():
        command = "nvidia-smi --query-gpu=memory.free --format=csv"
        memory_free_info = sp.check_output(command.split()).decode('ascii').split('\n')[:-1][1:]
        memory_free_values = [int(x.split()[0]) for i, x in enumerate(memory_free_info)]

        command = "nvidia-smi --query-gpu=memory.total --format=csv"
        memory_total_info = sp.check_output(command.split()).decode('ascii').split('\n')[:-1][1:]
        memory_total_values = [int(x.split()[0]) for i, x in enumerate(memory_total_info)]

        gpu_usage = [
            (memory_total_values[i] - memory_free_values[i]) / memory_total_values[i] * 100
            for i in range(len(memory_total_values))
        ]
        return gpu_usage

    while True:
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        gpu = get_gpu_percentage()
        out = json.dumps({
            'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'cpu': cpu,
            'mem': mem,
            'gpu': gpu
        })
        yield f"data:{out}\n\n"
        await asyncio.sleep(1)


# @app.websocket("/resource_data")
# async def resource_websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     while True:
#         await asyncio.sleep(1)
#         await websocket.send_json(next(resource_tracker()))


@app.get("/resource/data")
async def resource_data_endpoint(request: Request):
    response = StreamingResponse(resource_tracker(request), media_type="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response


@app.get("/resource", response_class=FileResponse)
def resource():
    return 'pages/resource.html'


# ---------------------------------- root ----------------------------------


@app.get("/")
def root():
    return 'Hello, World!'



