import websocket
import time

url = 'ws://oj-10-30-15-9-46057.adworld.xctf.org.cn/ws'
ws = websocket.create_connection(url, subprotocols=['tty'], timeout=10, origin='http://oj-10-30-15-9-46057.adworld.xctf.org.cn')
print('connected')
ws.send('{"columns":120,"rows":40}')
end = time.time() + 3
while time.time() < end:
    try:
        data = ws.recv()
        print(repr(data)[:500])
    except Exception as e:
        print('recv1', type(e).__name__, e)
        break
ws.send('0ctf\n')
end = time.time() + 3
while time.time() < end:
    try:
        data = ws.recv()
        print(repr(data)[:500])
    except Exception as e:
        print('recv2', type(e).__name__, e)
        break
ws.send('0ctf\n')
end = time.time() + 5
while time.time() < end:
    try:
        data = ws.recv()
        print(repr(data)[:800])
    except Exception as e:
        print('recv3', type(e).__name__, e)
        break
ws.close()
