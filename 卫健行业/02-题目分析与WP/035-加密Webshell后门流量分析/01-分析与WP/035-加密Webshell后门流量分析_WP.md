# 035-加密Webshell后门流量分析 WP

## 一、题目信息

| 项目 | 内容 |
| --- | --- |
| 题号 | 035 |
| 题目名称 | 加密Webshell后门流量分析 |
| 题型 | 附件分析题 |
| 提交格式 | `flag{xxx}` |
| 题目目标 | 某单位网络遭受攻击，请对提取到的网络流量数据进行分析 |
| 附件 | `LL.pcapng`（22 MB） |

## 二、分析思路

本题附件为一个 22 MB 的 pcapng 流量包，共约 28047 个数据包，几乎全部为 TCP 流量，通信双方为 `192.168.148.1`（攻击者）与 `192.168.148.136:80`（目标 Web 服务器）。

流量整体可分为两个明显阶段：**前期大规模扫描探测**与**后期精准漏洞利用及 Webshell 控制**。前期包含数千条 GET 请求，涵盖路径爆破、备份文件探测、常见漏洞路径扫描等；后期则集中在两个关键入口：`/_ignition/execute-solution`（Laravel Ignition 反序列化漏洞利用）与 `/about.php`（落地的加密 Webshell）。

分析重点不在于统计扫描流量，而在于还原**漏洞利用链条**与**Webshell 控制操作**，最终从加密响应中提取 flag。

## 三、攻击链还原

### 1. 漏洞利用：Laravel Ignition CVE-2021-3129

攻击者识别到目标运行 **Laravel 框架**（路径为 `D:\phpstudy_pro\WWW\laravel`），并利用 **CVE-2021-3129**（Ignition 组件 `MakeViewVariableOptionalSolution` 的任意文件写入漏洞）植入 Webshell。

该漏洞的利用链分为以下步骤：

| 步骤 | 请求 | 状态码 | 说明 |
| --- | --- | --- | --- |
| 1 | POST `/_ignition/execute-solution` | 200 | 通过 `php://filter` 链清空 `laravel.log`（写入空内容） |
| 2 | POST `/_ignition/execute-solution` | 200 | 再次清空日志，确保日志文件为空 |
| 3 | POST `/_ignition/execute-solution` | 500 | 探测目标路径（`viewFile=AA`），触发错误确认漏洞存在 |
| 4 | POST `/_ignition/execute-solution` | 500 | 向 `laravel.log` 写入经过 quoted-printable + UTF-16LE 编码的 PHAR 格式 PHP Webshell 序列化载荷 |
| 5 | POST `/_ignition/execute-solution` | 500 | 通过 `php://filter` 链将 `laravel.log` 中的编码内容解码还原为合法 PHP 文件，写入 `../storage/logs/laravel.log` |

步骤 4 写入的载荷解码后可以识别出 PHAR 文件头 `<?php __HALT_COMPILER(); ?>`，后接一个 PHP 反序列化对象 `Illuminate\Broadcasting\PendingBroadcast`，这是 Laravel 框架中已知的 POP 链入口。

### 2. Webshell 落地：`/about.php`

利用链执行成功后，Webshell 落地于 `/about.php`。该 Webshell 使用 **Godzilla（哥斯拉）** 工具管理，加密方式为 **PHP_AES 模式**：

- **加密算法**：AES-128-CBC
- **密钥**：`md5("rebeyond")[0:16]`（即 `d41d8cd98f00b204`）
- **IV**：`md5("rebeyond")[16:32]`（即 `e9800998ecf8427e`）
- **密码**：`rebeyond`（Godzilla 默认密码）

### 3. Godzilla 控制操作序列

攻击者通过 Godzilla 对目标服务器进行了以下操作：

| 操作序号 | 请求体大小 | 响应体大小 | 操作内容 | 响应内容 |
| --- | --- | --- | --- | --- |
| 操作 1 | GET（初始探测） | — | 验证 Webshell 是否可访问 | 200 OK |
| 操作 2 | 51693 B | 2476 B | 文件管理（目录浏览） | 目录列表（加密） |
| 操作 3 | 12223 B | 108 B | 获取当前工作路径 | `D:\phpstudy_pro\WWW\laravel` |
| 操作 4 | 24813 B | 64 B | 其他操作 | 空响应 |
| 操作 5 | 5804 B | 128 B | 命令执行（读取 flag） | **`flag{6ao6bnliyelpf2m5wudmt8ldudtnger8}`** |

## 四、解密过程

Godzilla PHP_AES 模式的解密步骤如下：

1. 对响应体进行 HTTP chunked 解码，得到原始 Base64 字符串
2. 对 Base64 字符串进行解码，得到 AES 密文
3. 使用 AES-128-CBC 解密，密钥和 IV 均由 `md5("rebeyond")` 派生
4. 解密后得到 JSON 格式响应，其中 `msg` 字段为 Base64 编码的实际内容
5. 对 `msg` 进行 Base64 解码，得到明文

操作 5 的响应解密过程：

```
响应体（chunked解码后）: mAUYLzmqn5QPDkyI5lvSp0fjiBu1e7047YjfczwY6j76ltx/...
↓ AES-128-CBC 解密（key=d41d8cd98f00b204, iv=e9800998ecf8427e）
↓ JSON: {"status":"c3VjY2Vzcw==","msg":"ZmxhZ3s2YW82Ym5saXllbHBmMm01d3VkbXQ4bGR1ZHRuZ2VyOH0="}
↓ Base64 解码 msg 字段
flag{6ao6bnliyelpf2m5wudmt8ldudtnger8}
```

## 五、答案

```text
flag{6ao6bnliyelpf2m5wudmt8ldudtnger8}
```

## 六、结论说明

本题的核心难点在于两层：其一是识别 **CVE-2021-3129** 漏洞利用链，理解攻击者如何通过 `php://filter` 链将 PHAR 格式载荷写入 Laravel 日志文件并触发反序列化；其二是识别 **Godzilla PHP_AES 加密模式**，并用正确的密钥派生方式（`md5(password)[0:16]` 作为 key，`md5(password)[16:32]` 作为 IV）完成 AES-128-CBC 解密。

最容易误判的地方是把前期大量扫描流量当作主要分析对象。实际上，扫描阶段几乎全部返回 404，真正有价值的流量集中在 7 条 Ignition 利用请求和 4 条 Godzilla 控制请求中。只要识别出 Webshell 工具类型和默认密码，解密过程即可自动化完成。
