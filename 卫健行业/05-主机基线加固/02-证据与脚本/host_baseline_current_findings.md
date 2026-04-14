# 主机基线加固题当前发现

## 题目要求

题目 README 明确要求：设置主机密码复杂度，要求密码长度最少 8 位，且至少包含 1 个大写字母、1 个小写字母、2 个数字、1 个特殊符号。裁判机每隔 15 秒检查一次，如果加固成功则生成 `/flag` 文件。

## 已确认环境

| 项目 | 结果 |
| --- | --- |
| 终端入口 | `ws://oj-10-30-15-2-46537.adworld.xctf.org.cn/ws` |
| 终端登录凭据 | `ctf/ctf` |
| 当前用户 | `ctf` |
| 主机名 | `a030d072beb2` |
| 系统 | Ubuntu 20.04.6 LTS |
| 可写关键文件 | `/etc/pam.d/common-password`（权限 `-rwxrwxrwx`） |
| 判题方式 | 轮询检查密码复杂度策略，满足后生成 `/flag` |

## 初始密码策略

初始 `/etc/pam.d/common-password` 中关键行为：

```text
password requisite pam_cracklib.so retry=3 minlen=8 difok=3
```

该配置只明确限制了最短长度与口令差异，不满足题目对大小写、数字数量、特殊字符的复杂度要求。

## 最终修复动作

将上述策略改为：

```text
password requisite pam_cracklib.so retry=3 minlen=8 difok=3 ucredit=-1 lcredit=-1 dcredit=-2 ocredit=-1
```

其中：

- `ucredit=-1`：至少 1 个大写字母
- `lcredit=-1`：至少 1 个小写字母
- `dcredit=-2`：至少 2 个数字
- `ocredit=-1`：至少 1 个其他字符（特殊符号）

## 修改命令

```bash
cp /etc/pam.d/common-password /tmp/common-password.bak
perl -0pi -e 's/pam_cracklib\.so\s+retry=3\s+minlen=8\s+difok=3/pam_cracklib.so retry=3 minlen=8 difok=3 ucredit=-1 lcredit=-1 dcredit=-2 ocredit=-1/' /etc/pam.d/common-password
```

## 结果

约 10 秒后 `/flag` 生成，内容为：

```text
xctf{32b394377d7a44d69d98df63a59f78e6b89cb4d8}
```
