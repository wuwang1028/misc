import time
import websocket

URL = 'ws://oj-10-30-15-9-46057.adworld.xctf.org.cn/ws'
ORIGIN = 'http://oj-10-30-15-9-46057.adworld.xctf.org.cn'


def connect(retries=6, delay=2):
    last = None
    for i in range(retries):
        try:
            ws = websocket.create_connection(URL, subprotocols=['tty'], timeout=10, origin=ORIGIN)
            return ws
        except Exception as e:
            last = e
            print(f'connect_retry_{i+1}: {type(e).__name__}: {e}')
            time.sleep(delay)
    raise last


def recv_text(ws, duration=2.0):
    end = time.time() + duration
    chunks = []
    while time.time() < end:
        timeout_left = max(0.2, min(1.0, end - time.time()))
        ws.settimeout(timeout_left)
        try:
            data = ws.recv()
        except Exception:
            continue
        if isinstance(data, (bytes, bytearray)):
            try:
                data = data.decode('utf-8', 'ignore')
            except Exception:
                data = repr(data)
        if not data:
            continue
        if data[0] == '0':
            chunks.append(data[1:])
        else:
            chunks.append(f'\n[[CTRL:{data!r}]]\n')
    return ''.join(chunks)


def send_cmd(ws, s, wait=2.5):
    ws.send('0' + s)
    time.sleep(0.4)
    out = recv_text(ws, wait)
    print(f'>>> SENT {s!r}')
    print(out)
    print('<<< END\n')
    return out


ws = connect()
print('CONNECTED')
ws.send('{"columns":140,"rows":40}')
print(recv_text(ws, 2.0))
send_cmd(ws, 'ctf\n', 2.0)
send_cmd(ws, 'ctf\n', 3.0)
for cmd in [
    'whoami; id; hostname; pwd\n',
    'ls -la /; echo ====; ls -la /home; echo ====; ls -la /var/www 2>/dev/null\n',
    'ps aux | head\n',
]:
    send_cmd(ws, cmd, 3.0)
ws.close()
