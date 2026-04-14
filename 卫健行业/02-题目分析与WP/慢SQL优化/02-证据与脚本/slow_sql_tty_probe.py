import asyncio
import websockets

URL = 'ws://oj-10-30-15-9-46057.adworld.xctf.org.cn/ws'

async def show(ws, rounds=8, timeout=2):
    for i in range(rounds):
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=timeout)
        except Exception as e:
            print('recv_timeout', type(e).__name__)
            return
        if isinstance(msg, bytes):
            print('bytes', msg[:200])
        else:
            print('text', repr(msg[:400]))

async def main():
    async with websockets.connect(URL, subprotocols=['tty'], open_timeout=10) as ws:
        print('connected', ws.subprotocol)
        await ws.send('{"columns":120,"rows":40}')
        await show(ws, 5, 2)
        await ws.send('{ hello }')
        await show(ws, 5, 2)
        await ws.send('0ctf\n')
        await show(ws, 8, 2)
        await ws.send('0ctf\n')
        await show(ws, 12, 2)

asyncio.run(main())
