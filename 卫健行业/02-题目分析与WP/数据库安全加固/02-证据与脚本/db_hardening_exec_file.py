import sys
import time
import uuid
import websocket

URL = 'ws://oj-10-30-15-12-45703.adworld.xctf.org.cn/ws'
ORIGIN = 'http://oj-10-30-15-12-45703.adworld.xctf.org.cn'


def recv_until_contains(ws, marker, timeout=25):
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
    if len(sys.argv) != 2:
        print('usage: python3.11 db_hardening_exec_file.py <command_file>')
        return
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        cmd = f.read().rstrip('\n')
    marker = 'CMDDONE_' + uuid.uuid4().hex
    ws = websocket.create_connection(
        URL,
        subprotocols=['tty'],
        timeout=20,
        origin=ORIGIN,
        enable_multithread=True,
    )
    ws.send('{"columns":200,"rows":55}')
    recv_until_contains(ws, 'login:', 8)
    ws.send('0ctf\n')
    recv_until_contains(ws, 'Password:', 8)
    ws.send('0ctf\n')
    recv_until_contains(ws, '$ ', 12)
    ws.send('0' + cmd + f"\necho {marker}\n")
    out = recv_until_contains(ws, marker, 90)
    print(out)
    ws.close()


if __name__ == '__main__':
    main()
