import sys
import time
import websocket

URL='ws://oj-10-30-15-9-46057.adworld.xctf.org.cn/ws'
ORIGIN='http://oj-10-30-15-9-46057.adworld.xctf.org.cn'
PROMPT=':~$ '
cmd=' '.join(sys.argv[1:])
if not cmd:
    print('usage: python slow_sql_exec_cmd.py <command>')
    sys.exit(1)

def connect(retries=12, delay=2):
    last=None
    for i in range(retries):
        try:
            return websocket.create_connection(URL, subprotocols=['tty'], timeout=10, origin=ORIGIN)
        except Exception as e:
            last=e
            print(f'connect_retry_{i+1}: {type(e).__name__}: {e}', file=sys.stderr)
            time.sleep(delay)
    raise last

def recv_until(ws, markers, timeout=20):
    end=time.time()+timeout
    buf=''
    while time.time()<end:
        ws.settimeout(max(0.3,min(1.2,end-time.time())))
        try:
            data=ws.recv()
        except Exception:
            continue
        if isinstance(data,(bytes,bytearray)):
            data=data.decode('utf-8','ignore')
        if not data:
            continue
        buf += data[1:] if data[0]=='0' else ''
        if any(m in buf for m in markers):
            break
    return buf

def login_and_run():
    ws=connect()
    ws.send('{"columns":200,"rows":55}')
    recv_until(ws,['login:'],5)
    ws.send('0ctf\n')
    recv_until(ws,['Password:'],8)
    ws.send('0ctf\n')
    recv_until(ws,[PROMPT,'Login incorrect'],15)
    time.sleep(0.5)
    ws.send('0'+cmd+'\n')
    out=recv_until(ws,[PROMPT],30)
    ws.close()
    return out

for attempt in range(2):
    try:
        print(login_and_run())
        break
    except Exception as e:
        if attempt == 1:
            raise
        print(f'run_retry_{attempt+1}: {type(e).__name__}: {e}', file=sys.stderr)
        time.sleep(2)
