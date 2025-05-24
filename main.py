import json

from device import Device, Command
from fastapi import FastAPI, HTTPException, Depends
import redis.asyncio as redis
from typing import List, Optional

app = FastAPI()


# Declare application parameters
REDIS_HOSTNAME = "localhost"
REDIS_PORT = 6379


# Redis async connection
async def get_redis():
    redis_client = redis.Redis(host=REDIS_HOSTNAME, port=REDIS_PORT, db=0, decode_responses=True)
    try:
        yield redis_client
    finally:
        await redis_client.close()


# Define the REST endpoints
@app.get("/devices", response_model=List[Device])
async def get_devices(r: redis.Redis = Depends(get_redis)):
    keys = await r.keys("device:*")
    devices = []
    for key in keys:
        data = await r.get(key)
        devices.append(json.loads(data))

    return devices


# Add a new device
@app.post("/devices", response_model=Device)
async def add_device(device: Device, r: redis.Redis = Depends(get_redis)):
    await r.set(f"device:{device.id}", device.json())
    return device


# Get single device by ID
@app.get("/devices/{device_id}", response_model=Device)
async def get_device(device_id: str, r: redis.Redis = Depends(get_redis)):
    data = await r.get(f"device:{device_id}")
    if data is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return json.loads(data)


# Deletes a device by ID
@app.delete("/devices/{device_id}")
async def delete_device(device_id: str, r: redis.Redis = Depends(get_redis)):
    data = await r.get(f"device:{device_id}")
    if data is None:
        raise HTTPException(status_code=404, detail="Device not found")
    await r.delete(device_id)
    return {"msg": f"Device {device_id} deleted"}


# Sends a command to a device
@app.post("/devices/{device_id}/command")
async def send_command(device_id: str, command: Command, r: redis.Redis = Depends(get_redis)):
    data = await r.get(f"device:{device_id}")
    if data is None:
        raise HTTPException(status_code=404, detail="Device not found")
    device = Device(**json.loads(data))

    if command.action == "status":
        device.status = command.value
        device.command_history.append(f"Set status to {command.value}")

    await r.set(f"device:{device_id}", device.model_dump_json())
    return {"message": f"Command sent to device {device_id}", "device": device}
