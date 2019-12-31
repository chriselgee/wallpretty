#!/usr/bin/python3
import inspect
import random
from os import path

from flask import Flask, redirect, render_template, request, url_for
from flask_socketio import SocketIO

OV = '\x1b[0;33m' # verbose
OR = '\x1b[0;34m' # routine
OE = '\x1b[1;31m' # error
OM = '\x1b[0m'    # mischief managed
file_path = path.dirname(path.realpath(__file__))

debuggin = False
with open(file_path+'/wall.conf') as f:
  for line in f:
    if "debuggin" in line and "True" in line:
      debuggin = True
      print(OV+"Debuggin turned on in wall-pretty-server.py!"+OM)

# load chunks of HTML to be used in building pages
with open(file_path+'/html/header.html') as f:
  html_header = f.read()
with open(file_path+'/html/footer.html') as f:
  html_footer = f.read()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'vnkdjnfjknfl1232#'
socketio = SocketIO(app)


@app.route('/')
def index():
    return render_template('index.html')


def messageReceived(methods=['GET', 'POST']):
    print('message was received!!!')


@socketio.on('chatter')
def chat_event(json, methods=['GET', 'POST']):
    print(f'{OR}received chatter: {str(json)}{OM}')
    if debuggin: print(f"{OV}json looks like {OR}{json}{OM}")
    if 'message' in json:
      if debuggin: print(f"{OV}message looks like {OR}{json['message']}{OV} and it's {OR}{len(json['message'])}{OV} long{OM}")
      if len(json['message']) > 0:
        socketio.emit('my response', json, callback=messageReceived)
    


if __name__ == '__main__':
    socketio.run(app, debug=debuggin)
