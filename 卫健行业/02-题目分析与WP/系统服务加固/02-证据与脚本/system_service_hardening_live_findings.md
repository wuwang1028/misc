# 系统服务加固现场记录

## 已确认环境信息

- 成功完成的实例地址：`http://oj-10-30-15-9-42721.adworld.xctf.org.cn/`
- ttyd 登录凭据：`ctf / ctf`
- `/home/ctf/README.md` 明确说明：Redis 端口为 `6379`，FTP 加固后可执行 `sudo /restart-ftp.sh` 重启，裁判每隔约 15 秒检查一次，成功后会生成 `/flag`。
- 进程侧确认：`redis-server`、`vsftpd /etc/vsftpd/vsftpd.conf`、`/root/check/judge.py`、`ttyd -p 8080 login` 同时存在。
- 关键权限确认：
  - `/etc/vsftpd/vsftpd.conf` 为 `-rwxrwxrwx`，可被 `ctf` 直接改写；
  - `sudo -l` 显示 `ctf` 可无密码执行 `/restart-ftp.sh`；
  - `/restart-ftp.sh` 内容为 `pkill vsftpd && vsftpd /etc/vsftpd/vsftpd.conf &`。

## 已确认风险点

### 1. FTP 侧风险

通过交互确认：

- 匿名 FTP 登录原本可用；
- FTP `PORT` 主动模式可被使用，存在与内网 Redis 端口联动的风险；
- `/etc/vsftpd/vsftpd.conf` 为 world-writable，属于明显的高风险配置文件暴露。

### 2. Redis 侧风险

真正的关键线索并不只是 FTP。本题裁判脚本会先检查 Redis 是否启用了认证；如果 Redis 仍然无口令，则即使 FTP 已经加固，依然不会出 flag。

## 真实判题逻辑

通过利用 `sudo /restart-ftp.sh` 调用 `vsftpd` 时会解析可控 `PATH` 这一点，导出了 `/root/check/judge.py`，确认裁判逻辑如下：

1. 连接 `127.0.0.1:6379`；
2. 发送 `AUTH aaaaaaaaaaaaaaaaaaaaaaaaaaaaa`；
3. 若返回 `called without any password configured for the default user`，判定失败；
4. 若返回 `WRONGPASS`，再继续检查匿名 FTP 登录；
5. 只有在 **Redis 已启用口令** 且 **匿名 FTP 登录失败** 时，才会生成 `/flag`。

## 最终有效修复动作

### 一、FTP 加固

在 `/etc/vsftpd/vsftpd.conf` 中确认并保留：

- `anonymous_enable=NO`
- `port_enable=NO`

然后执行：

- `sudo /restart-ftp.sh`

### 二、Redis 加固

通过本地 socket 向 Redis 下发：

- `CONFIG SET requirepass Manus123`

随后验证：

- 错误口令 `AUTH aaaaaaaaaaaaaaaaaaaaaaaaaaaaa` 返回 `WRONGPASS invalid username-password pair or user is disabled.`
- 正确口令 `AUTH Manus123` 返回 `+OK`

### 三、补充处理

- 已将 `/home/ctf/.ash_history` 处理为指向 `/dev/null` 的符号链接，但这不是最终判题的必要条件。
- `seccomp_sandbox=YES` 会导致服务不可用，因此不是本题最终通过判题所需的配置。

## 最终结果

等待一个判题周期后，成功生成：

- `/flag`
- flag 内容：`xctf{0c8ad26cb1fb4cc4855b73dce8739c8a81fe78f4}`

## 复盘结论

这题的误导点在于：题面会让人优先聚焦 FTP 与 `PORT` 跳板，但裁判逻辑实际要求的是一组**组合修复条件**：

1. Redis 必须开启认证；
2. FTP 匿名登录必须关闭。

因此，单做 FTP 加固并不足以通过判题，必须同时完成 Redis 认证配置。
