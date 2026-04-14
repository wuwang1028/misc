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


def recv_until(ws, markers, timeout=20):
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
        buf += data[1:] if data[0] == '0' else f'\n[[CTRL:{data!r}]]\n'
        if any(m in buf for m in markers):
            break
    return buf


def send_and_wait(ws, line, markers=None, timeout=20):
    if markers is None:
        markers = [PROMPT]
    ws.send('0' + line + '\n')
    out = recv_until(ws, markers, timeout)
    print(f'===== SENT: {line!r} =====')
    print(out)
    print('===== END =====\n')
    return out

ws = connect()
ws.send('{"columns":180,"rows":50}')
print(recv_until(ws, ['login:'], 5))
send_and_wait(ws, 'ctf', ['Password:'], 8)
send_and_wait(ws, 'ctf', [PROMPT, 'Login incorrect'], 15)
cmds = [
    'cat /start.sh',
    'ls -R /root/check 2>/dev/null',
    'sed -n "1,240p" /root/check/judge.py 2>/dev/null',
    'mysql -uctf -pctf -e "show databases;"',
    'mysql -uctf -pctf -e "select user,host from mysql.user;"',
    'mysql -uctf -pctf -e "show grants for current_user();"',
]
for c in cmds:
    send_and_wait(ws, c, [PROMPT], 20)
ws.close()
