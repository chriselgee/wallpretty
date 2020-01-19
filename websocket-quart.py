#!/usr/bin/env python3
from functools import wraps
from quart import Quart, render_template, websocket, copy_current_websocket_context, request
import asyncio
import json
from ws2801_funcs import rainbow_cycle

OV = '\x1b[0;33m' # verbose
OR = '\x1b[0;34m' # routine
OE = '\x1b[1;31m' # error
OM = '\x1b[0m'    # mischief managed

debuggin = True


app = Quart(__name__)
connected = set()


def collect_websocket(func):
    # when someone connects to /ws, add to inventory of websockets
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if debuggin: print(f'{OV}entered wrapper(){OM}')
        global connected
        connected.add(websocket._get_current_object())
        try:
            return await func(*args, **kwargs)
        finally:
            connected.remove(websocket._get_current_object())
    return wrapper


async def broadcast(message):
    # broadcast a message to all connected websockets
    if debuggin: print(f'{OV}entered broadcast(){OM}')
    for websock in connected:
        await websock.send(message)


async def consumer():
    # what to do with incoming websocket messages
    while True:
        if debuggin: print(f'{OV}entered consumer(){OM}')
        data = await websocket.receive()
        # await broadcast(data)
        if debuggin: print(f'{OV}received data {OR}{data}{OM}', end='')
        try:
            dataj = json.loads(data)
            if dataj["Type"] == "Chat":
                if debuggin: print(f'{OV}, broadcasting as chat {OM}')
                if dataj["Data"].lower() == "rainbow":
                    rainbow_cycle()
                await broadcast(f'{{"Type":"Chat","Data":"{dataj["Data"]}"}}')
            if dataj["Type"] == "Pixel":
                # update the board
                if debuggin: print(f'{OV}, broadcasting as pixel {OM}')
                await broadcast(f'{{"Type":"Pixel","Data":"{dataj["Data"]}"}}')
        except Exception as ex: # catch exceptions
            print(f'{OE}*** Exception in websocket-quart.py, consumer(): {OR}{ex}{OM}') 
            # return {"Success":False, "Error":f"{inspect.currentframe().f_code.co_name}-Exception: {ex}"}



async def producer():
    # sends sample messages out on a schedule
    while True:
        if debuggin: print(f'{OV}entered producer(){OM}')
        message = f'{{"Type":"System","Data":"I\'m watching"}}'
        await asyncio.sleep(60)
        await websocket.send(message)
        if debuggin: print(f'{OV}sent message {OR}{message}{OM}')


@app.websocket('/ws')
# defines what to do when websockets are requested from a client
@collect_websocket
async def ws():
    if debuggin: print(f'{OV}entered ws(){OM}')
    await broadcast('{"Type":"System","Data":"Someone connected"}')
    # await broadcast(b'{"Type":"System","Data":"This is a byte string yo!"}')
    consumer_task = asyncio.ensure_future( # copy websocket to consumer()
        copy_current_websocket_context(consumer)(),
    )
    producer_task = asyncio.ensure_future( # copy websocket to producer()
        copy_current_websocket_context(producer)(),
    )
    try:
        result = await asyncio.gather(consumer_task, producer_task)
        if debuggin: print(f'{OV}result is {OR}{result}{OM}')
    finally:
        consumer_task.cancel()
        producer_task.cancel()

@app.route('/')
# defines behavior for clients requesting /
async def index():
    if debuggin: print(f'{OV}/ requested via {OR}{request.method}{OM}')
    width = 10 # manually setting size of grid
    height = 20
    # build a list of x, y values for render to iterate through, e.g. 0,0 through 9,19
    xs, ys = [], []
    for i in range(width):
            xs += [i,]
    for i in range(height):
            ys += [(height - i - 1),]
    return await render_template('index.html', xs=xs, ys=ys, height=height)

if __name__ == '__main__':
    app.run(port=5000)
