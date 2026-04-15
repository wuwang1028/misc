import sys
import time
import json
import requests
import websocket

if len(sys.argv) != 6:
    print('usage: deploy_ttyd_b64.py <base_url> <user> <pass> <local_b64_file> <remote_jar_path>')
    sys.exit(1)

BASE = sys.argv[1].rstrip('/')
USER = sys.argv[2]
PASS = sys.argv[3]
LOCAL_B64 = sys.argv[4]
REMOTE_JAR = sys.argv[5]
REMOTE_B64 = REMOTE_JAR + '.b64'

with open(LOCAL_B64, 'r', encoding='utf-8') as f:
    b64 = f.read().strip()

session = requests.Session()
token = ''
try:
    r = session.get(BASE + '/token', timeout=10)
    if r.ok:
        token = r.json().get('token', '')
except Exception:
    pass

ws_url = BASE.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws'
ws = websocket.create_connection(ws_url, subprotocols=['tty'], timeout=10)
ws.settimeout(1)
ws.send(json.dumps({'AuthToken': token, 'columns': 120, 'rows': 40}))

out = []

def recv_for(seconds=0.6):
    end = time.time() + seconds
    while time.time() < end:
        try:
            msg = ws.recv()
            if isinstance(msg, bytes) and msg:
                tag = chr(msg[0])
                if tag == '0':
                    out.append(msg[1:].decode('utf-8', 'ignore'))
            elif isinstance(msg, str):
                out.append(msg)
        except Exception:
            time.sleep(0.03)


def send_line(line, wait=0.15):
    ws.send(('0' + line + '\n').encode())
    time.sleep(wait)
    recv_for(0.2)

recv_for(1.5)
send_line(USER, 0.3)
recv_for(0.6)
send_line(PASS, 0.4)
recv_for(1.0)

send_line(': > ' + REMOTE_B64, 0.1)
chunk_size = 240
for i in range(0, len(b64), chunk_size):
    chunk = b64[i:i+chunk_size]
    send_line("printf '%s' '" + chunk + "' >> " + REMOTE_B64, 0.05)

send_line('base64 -d ' + REMOTE_B64 + ' > ' + REMOTE_JAR, 0.2)
send_line('ls -lh ' + REMOTE_JAR + ' ' + REMOTE_B64, 0.2)
send_line('wc -c ' + REMOTE_JAR + ' ' + REMOTE_B64, 0.2)
recv_for(2.5)
ws.close()
print(''.join(out))
