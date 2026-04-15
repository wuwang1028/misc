import sys
import time
import json
import requests
import websocket

BASE = sys.argv[1].rstrip('/')
USER = sys.argv[2]
PASS = sys.argv[3]
COMMANDS = sys.argv[4:]

session = requests.Session()
token = ''
try:
    r = session.get(BASE + '/token', timeout=10)
    if r.ok:
        token = r.json().get('token', '')
except Exception:
    token = ''

ws_url = BASE.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws'
ws = websocket.create_connection(ws_url, subprotocols=['tty'], timeout=10)
ws.settimeout(1)
ws.send(json.dumps({'AuthToken': token, 'columns': 120, 'rows': 40}))

buf = []

def recv_for(seconds):
    end = time.time() + seconds
    while time.time() < end:
        try:
            msg = ws.recv()
            if isinstance(msg, str):
                data = msg
            else:
                data = bytes(msg)
                if not data:
                    continue
                tag = chr(data[0])
                payload = data[1:]
                if tag == '0':
                    try:
                        buf.append(payload.decode('utf-8', 'ignore'))
                    except Exception:
                        buf.append(repr(payload))
                elif tag == '1':
                    try:
                        buf.append('\n[TITLE]' + payload.decode('utf-8', 'ignore') + '\n')
                    except Exception:
                        pass
                elif tag == '2':
                    try:
                        buf.append('\n[OPTIONS]' + payload.decode('utf-8', 'ignore') + '\n')
                    except Exception:
                        pass
        except Exception:
            time.sleep(0.05)


def send_line(s):
    ws.send(('0' + s + '\n').encode())
    time.sleep(0.3)

recv_for(2)
send_line(USER)
recv_for(1)
send_line(PASS)
recv_for(1.5)
for cmd in COMMANDS:
    send_line(cmd)
    recv_for(1.2)
recv_for(2)
ws.close()
print(''.join(buf))
