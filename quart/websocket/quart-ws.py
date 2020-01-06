#!/usr/bin/env python3
from quart import Quart, render_template, websocket, copy_current_websocket_context
from functools import partial, wraps
import asyncio

OV = '\x1b[0;33m' # verbose
OR = '\x1b[0;34m' # routine
OE = '\x1b[1;31m' # error
OM = '\x1b[0m'    # mischief managed

debuggin = True


app = Quart(__name__)
connected_websockets = set()

def collect_websocket(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        global connected_websockets
        queue = asyncio.Queue()
        connected_websockets.add(queue)
        if debuggin: print(f'{OV}in collect_websocket(), connected_websockets looks like {OR}{connected_websockets}{OM}')
        try:
            return await func(queue, *args, **kwargs)
        finally:
            connected_websockets.remove(queue)
    return wrapper

async def broadcast(message):
    if debuggin: print(f'{OV}broadcasting {OR}{message}{OM}')
    if debuggin: print(f'{OV}in broadcast(), connected_websockets looks like {OR}{connected_websockets}{OM}')
    for websock in connected_websockets:
        if debuggin: print(f'{OV}broadcasting to {OR}{websock}{OM}')
        await websock.send(message)

@app.route('/')
async def index():
    return await render_template('index.html')

@app.websocket('/ws')
async def ws():
    while True:
        data = await websocket.receive()
        if debuggin: print(f'{OV}got data {OR}{data}{OM}')
        await websocket.send(f"echo {data}")
        await broadcast(f"broadcasting {data}")

@app.websocket('/api/v2/ws')
@collect_websocket
async def wsbcast(queue):
    while True:
        data = await queue.get()
        if debuggin: print(f'{OV}wsbcast got data {OR}{data}{OM}')
        await websocket.send(data)

if __name__ == '__main__':
    app.run(port=5000)
