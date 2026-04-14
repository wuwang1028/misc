import time
import websocket

URL = 'ws://oj-10-30-15-9-46057.adworld.xctf.org.cn/ws'
ORIGIN = 'http://oj-10-30-15-9-46057.adworld.xctf.org.cn'
PROMPT = ':~$ '


def connect(retries=10, delay=2):
    last = None
    for i in range(retries):
        try:
            return websocket.create_connection(URL, subprotocols=['tty'], timeout=10, origin=ORIGIN)
        except Exception as e:
            last = e
            print(f'connect_retry_{i+1}: {type(e).__name__}: {e}')
            time.sleep(delay)
    raise last


def recv_until(ws, markers, timeout=12):
    end = time.time() + timeout
    buf = ''
    while time.time() < end:
        ws.settimeout(max(0.5, min(2.0, end - time.time())))
        try:
            data = ws.recv()
        except Exception:
            continue
        if isinstance(data, (bytes, bytearray)):
            data = data.decode('utf-8', 'ignore')
        if not data:
            continue
        if data[0] == '0':
            buf += data[1:]
        else:
            buf += f'\n[[CTRL:{data!r}]]\n'
        if any(m in buf for m in markers):
            break
    return buf


def send_and_wait(ws, line, markers, timeout=12):
    ws.send('0' + line + '\n')
    out = recv_until(ws, markers, timeout)
    print(f'===== SENT: {line!r} =====')
    print(out)
    print('===== END =====\n')
    return out

ws = connect()
print('CONNECTED')
ws.send('{"columns":160,"rows":45}')
print(recv_until(ws, ['login:'], 5))
send_and_wait(ws, 'ctf', ['Password:'], 8)
send_and_wait(ws, 'ctf', [PROMPT, 'Login incorrect'], 15)
for cmd in [
    'echo READY; whoami; id; hostname; pwd',
    'ls -la /',
    'ls -la /home',
    'ls -la /var/www 2>/dev/null || true',
    'ps aux | head -20',
    'which mysql || which mariadb || ls /usr/bin | grep -E "mysql|maria"',
]:
    send_and_wait(ws, cmd, [PROMPT], 10)
ws.close()
