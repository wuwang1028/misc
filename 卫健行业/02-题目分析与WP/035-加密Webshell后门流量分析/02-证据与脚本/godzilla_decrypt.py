#!/usr/bin/env python3
"""
035-加密Webshell后门流量分析 - Godzilla PHP_AES 解密脚本

用法:
    python3 godzilla_decrypt.py <pcap_file>

依赖:
    pip3 install dpkt pycryptodome

说明:
    本脚本对 pcap/pcapng 文件中的 Godzilla PHP_AES 加密流量进行解密。
    Godzilla PHP_AES 模式参数:
      - 加密算法: AES-128-CBC
      - 密钥: md5(password)[0:16]
      - IV: md5(password)[16:32]
      - 默认密码: rebeyond
"""
import sys
import dpkt
import socket
import base64
import hashlib
import re
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


def ip_to_str(ip_bytes):
    try:
        return socket.inet_ntoa(ip_bytes)
    except:
        return str(ip_bytes)


def decode_chunked(data):
    """解码 HTTP chunked 传输编码"""
    result = b''
    pos = 0
    while pos < len(data):
        end = data.find(b'\r\n', pos)
        if end == -1:
            break
        size_str = data[pos:end].decode('ascii', errors='replace').strip()
        size_str = size_str.split(';')[0].strip()
        try:
            chunk_size = int(size_str, 16)
        except:
            break
        if chunk_size == 0:
            break
        pos = end + 2
        result += data[pos:pos + chunk_size]
        pos += chunk_size + 2
    return result if result else data


def safe_b64decode(s):
    """安全的 Base64 解码，自动补齐 padding"""
    if isinstance(s, str):
        s = s.encode()
    s = s.strip()
    padding = 4 - len(s) % 4
    if padding != 4:
        s += b'=' * padding
    return base64.b64decode(s)


def godzilla_aes_decrypt(data_b64, password='rebeyond'):
    """Godzilla PHP_AES 解密"""
    try:
        raw = safe_b64decode(data_b64)
        key_md5 = hashlib.md5(password.encode()).hexdigest()
        key = key_md5[:16].encode()
        iv = key_md5[16:32].encode()

        if len(raw) < 16 or len(raw) % 16 != 0:
            return None

        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(raw)

        try:
            decrypted = unpad(decrypted, 16)
        except:
            pass

        return decrypted
    except Exception:
        return None


def get_webshell_sessions(filename, webshell_path='/about.php'):
    """提取指定 Webshell 路径的所有请求响应对"""
    sessions = []

    with open(filename, 'rb') as f:
        try:
            pcap = dpkt.pcapng.Reader(f)
        except Exception:
            f.seek(0)
            pcap = dpkt.pcap.Reader(f)

        streams = {}
        for ts, buf in pcap:
            try:
                eth = dpkt.ethernet.Ethernet(buf)
                if not isinstance(eth.data, dpkt.ip.IP):
                    continue
                ip = eth.data
                src = ip_to_str(ip.src)
                dst = ip_to_str(ip.dst)

                if not isinstance(ip.data, dpkt.tcp.TCP):
                    continue
                tcp = ip.data
                if not tcp.data:
                    continue

                if tcp.dport == 80:
                    key = (src, tcp.sport, dst, tcp.dport)
                    direction = 'req'
                elif tcp.sport == 80:
                    key = (dst, tcp.dport, src, tcp.sport)
                    direction = 'resp'
                else:
                    continue

                if key not in streams:
                    streams[key] = {'req': b'', 'resp': b'', 'ts': ts}
                streams[key][direction] += tcp.data
            except Exception:
                pass

    for key, data in sorted(streams.items(), key=lambda x: x[1]['ts']):
        req_data = data['req']
        if not req_data or webshell_path.encode() not in req_data[:200]:
            continue

        header_end = req_data.find(b'\r\n\r\n')
        if header_end == -1:
            continue
        req_body = req_data[header_end + 4:]

        resp_data = data['resp']
        resp_body = b''
        resp_status = 0
        if resp_data:
            try:
                resp_status = int(resp_data.split(b'\r\n')[0].decode().split(' ')[1])
            except Exception:
                pass
            resp_header_end = resp_data.find(b'\r\n\r\n')
            if resp_header_end != -1:
                resp_raw = resp_data[resp_header_end + 4:]
                resp_body = decode_chunked(resp_raw)

        sessions.append({
            'key': key,
            'req_body': req_body,
            'resp_body': resp_body,
            'resp_status': resp_status
        })

    return sessions


def parse_godzilla_response(resp_decrypted):
    """解析 Godzilla 响应，提取 msg 字段"""
    if not resp_decrypted:
        return None
    try:
        text = resp_decrypted.decode('utf-8', errors='replace')
        m = re.search(r'"msg":"([A-Za-z0-9+/=]*)"', text)
        if m:
            msg_b64 = m.group(1)
            try:
                return safe_b64decode(msg_b64).decode('utf-8', errors='replace')
            except Exception:
                return msg_b64
        return text
    except Exception:
        return str(resp_decrypted[:200])


def main():
    filename = sys.argv[1] if len(sys.argv) > 1 else 'LL.pcapng'
    password = sys.argv[2] if len(sys.argv) > 2 else 'rebeyond'

    print(f"[*] 分析文件: {filename}")
    print(f"[*] 使用密码: {password}")
    print(f"[*] AES 密钥: {hashlib.md5(password.encode()).hexdigest()[:16]}")
    print(f"[*] AES IV:   {hashlib.md5(password.encode()).hexdigest()[16:32]}")

    sessions = get_webshell_sessions(filename)
    print(f"[*] 找到 {len(sessions)} 个 Webshell 会话\n")

    for i, sess in enumerate(sessions):
        req_body = sess['req_body']
        resp_body = sess['resp_body']

        if not req_body:
            continue

        print(f"{'=' * 60}")
        print(f"[会话 {i + 1}] 状态: {sess['resp_status']} | 请求: {len(req_body)}B | 响应: {len(resp_body)}B")

        # 解密响应
        if resp_body:
            resp_dec = godzilla_aes_decrypt(resp_body, password)
            if resp_dec:
                msg = parse_godzilla_response(resp_dec)
                if msg and msg.strip():
                    print(f"  响应内容: {msg[:300]}")
                    if 'flag' in msg.lower():
                        print(f"\n  [!!!] 发现 FLAG: {msg}")
            else:
                print(f"  [响应解密失败]")


if __name__ == '__main__':
    main()
