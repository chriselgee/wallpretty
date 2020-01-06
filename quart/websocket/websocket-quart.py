#!/usr/bin/env python3
from functools import wraps
from signal import signal, SIGINT
from sys import exit
from quart import Quart, render_template, websocket, copy_current_websocket_context, request
import asyncio

OV = '\x1b[0;33m' # verbose
OR = '\x1b[0;34m' # routine
OE = '\x1b[1;31m' # error
OM = '\x1b[0m'  # mischief managed

debuggin = True


app = Quart(__name__)
connected = set()


def collect_websocket(func):
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
  if debuggin: print(f'{OV}entered broadcast(){OM}')
  for websock in connected:
    await websock.send('New connection')


async def consumer():
  while True:
    if debuggin: print(f'{OV}entered consumer(){OM}')
    data = await websocket.receive()
    if debuggin: print(f'{OV}received data {OR}{data}{OM}')

async def producer():
  while True:
    if debuggin: print(f'{OV}entered producer(){OM}')
    message = "I'm watching"
    await asyncio.sleep(15)
    await websocket.send(message)
    if debuggin: print(f'{OV}sent message {OR}{message}{OM}')


@app.websocket('/ws')
@collect_websocket
async def ws():
  if debuggin: print(f'{OV}entered ws(){OM}')
  await broadcast(b'New connection established')
  consumer_task = asyncio.ensure_future(
    copy_current_websocket_context(consumer)(),
  )
  producer_task = asyncio.ensure_future(
    copy_current_websocket_context(producer)(),
  )
  try:
    result = await asyncio.gather(consumer_task, producer_task)
    if debuggin: print(f'{OV}result is {OR}{result}{OM}')
  finally:
    consumer_task.cancel()
    producer_task.cancel()

@app.route('/')
async def index():
  if debuggin: print(f'{OV}/ requested via {OR}{request.method}{OM}')
  return await render_template('index.html')

if __name__ == '__main__':
  app.run(port=5000)
