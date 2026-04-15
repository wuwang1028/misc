# 系统服务加固 WP

## 一、题目概述

本题的正式题名为 **系统服务加固**。题面提示这是一台新上线的服务器，要求识别其相关安全风险并完成加固；同时明确给出三条线索服务：**HTTP、Redis 6379 与 FTP 21**。实际进入环境后可以确认，浏览器入口首先呈现的是 ttyd 在线终端，终端登录身份为 `ctf/ctf`，成功判定的标志仍然是裁判周期性检查后生成 `/flag`。[1]

与第一眼观察不同，本题并不是单纯的 FTP 配置修补题。虽然题面与 README 都强调了 FTP 服务和 `sudo /restart-ftp.sh` 重启方式，但最终取证证明，裁判逻辑要求同时满足 **Redis 已开启认证** 与 **匿名 FTP 登录已被禁止** 两个条件，缺一不可。[1] [2]

| 项目 | 结果 |
| --- | --- |
| 题目名称 | `系统服务加固` |
| 终端登录身份 | `ctf/ctf` |
| 题面线索 | HTTP、Redis 6379、FTP 21 |
| 可用提权动作 | `sudo /restart-ftp.sh` |
| 最终判定 | `/flag` 生成即为通过 |

## 二、环境识别与初始风险判断

登录终端后，首先可以从 `/home/ctf/README.md` 与进程状态中确认：容器内同时运行 `redis-server`、`vsftpd /etc/vsftpd/vsftpd.conf`、`ttyd -p 8080 login` 以及 `/root/check/judge.py`。README 还明确指出，FTP 完成加固后可以执行 `sudo /restart-ftp.sh` 重启服务，裁判大约每 15 秒检查一次，成功后会生成 `/flag`。[1]

进一步检查关键权限可知，`ctf` 用户虽然不能直接获得完整 root shell，但具备两项对题目非常关键的操作条件：第一，`/etc/vsftpd/vsftpd.conf` 是可直接改写的 world-writable 文件；第二，`sudo -l` 显示 `ctf` 可以无密码执行 `/restart-ftp.sh`。这说明题目至少有一半以上的预期解法会落在 **FTP 配置修改 + 受控重启** 上。[1]

| 检查项 | 结果 | 结论 |
| --- | --- | --- |
| `/home/ctf/README.md` | 明确说明 Redis 端口、FTP 重启方式与判题周期 | 题目核心围绕服务配置加固 |
| `/etc/vsftpd/vsftpd.conf` | 权限为 `777` | `ctf` 可直接编辑 FTP 配置 |
| `sudo -l` | 允许执行 `/restart-ftp.sh` | 可完成 FTP 配置重载 |
| 进程列表 | 存在 `redis-server`、`vsftpd`、`judge.py` | Redis 与 FTP 都进入真实攻击面 |

## 三、FTP 侧风险确认

根据题面提示，最先应怀疑的是 **FTP 匿名访问与 FTP bounce/主动模式滥用**。对 `vsftpd.conf` 的检查可以看到，匿名访问与主动模式相关选项确实处于不安全状态；进一步交互验证也证明，匿名 FTP 登录原本可以成功，而 `PORT` 指令同样可用，这与题面故意强调 Redis `6379` 和 FTP `21` 的组合线索完全吻合。[1]

这意味着攻击者理论上可以把 FTP 作为一个对内网端口发起连接的跳板，或者至少通过匿名身份接触到不应暴露的服务能力。基于这一观察，最初的加固思路自然会聚焦到：关闭匿名 FTP、关闭 `PORT` 主动模式，并尝试恢复更保守的 `seccomp_sandbox` 设置。

| 风险点 | 现场表现 | 初步结论 |
| --- | --- | --- |
| 匿名 FTP | 原本允许匿名登录 | 需要关闭 |
| `PORT` 主动模式 | 可被使用 | 需要限制 |
| `seccomp_sandbox` | 关闭状态 | 看似可作为基础加固项 |
| 配置文件权限过宽 | `vsftpd.conf` 为 `777` | 属于明显高危配置暴露 |

## 四、误区与关键突破

在实际修复过程中，只做 FTP 侧加固并没有立即出 flag。即便已经把 `anonymous_enable=NO` 与 `port_enable=NO` 写入配置，并通过 `sudo /restart-ftp.sh` 完成重启，裁判依然没有生成 `/flag`。[1] 这说明题目真正的判题条件比表面看到的更复杂。

关键突破来自对 `/restart-ftp.sh` 调用方式的进一步分析。该脚本内容非常短，仅执行 `pkill vsftpd` 与 `vsftpd /etc/vsftpd/vsftpd.conf &`，而且命令使用的是**未写绝对路径的可执行名**。利用这一点，可以通过构造同名 `vsftpd` 包装脚本并在 `sudo` 执行时控制 `PATH`，让脚本先以 root 身份执行自定义动作，再继续真正启动系统的 `/usr/sbin/vsftpd`。[1] [2]

借助这个突破，成功把 `/root/check/judge.py` 导出到普通用户可读路径，并由此确认了真实裁判逻辑：裁判并不会只看 FTP，而是首先向 `127.0.0.1:6379` 发送 `AUTH aaaaaaaaaaaaaaaaaaaaaaaaaaaaa`。如果返回的是 “**called without any password configured for the default user**”，就直接判定修复失败；只有当返回 `WRONGPASS` 时，才会继续检查匿名 FTP 登录是否被拒绝。[2]

> 也就是说，本题最终通过条件不是“FTP 修好了”这么简单，而是：**Redis 必须启用认证，且 FTP 匿名登录必须失败。**

## 五、最终修复方案

在获得真实判题逻辑后，修复方案就变得非常明确。

首先，在 FTP 侧保留有效的限制项：把 `/etc/vsftpd/vsftpd.conf` 中的 `anonymous_enable` 设为 `NO`，并把 `port_enable` 设为 `NO`，然后通过 `sudo /restart-ftp.sh` 重启 FTP 服务。[1] 这一步可以确保匿名登录路径被关闭，同时阻断主动模式相关风险。

其次，在 Redis 侧补齐认证要求。由于本地 Redis 在未设置口令时允许直接执行配置命令，因此可以通过本地 socket 向 `127.0.0.1:6379` 发送 `CONFIG SET requirepass Manus123`，使 Redis 开始要求身份认证。[1] 随后再次验证可以看到，错误口令 `AUTH aaaaaaaaaaaaaaaaaaaaaaaaaaaaa` 返回 `WRONGPASS invalid username-password pair or user is disabled.`，而正确口令 `AUTH Manus123` 返回 `+OK`，这与裁判脚本的期待完全一致。[1] [2]

| 修复项 | 修复前风险 | 最终动作 |
| --- | --- | --- |
| `anonymous_enable` | 匿名用户可直接登录 FTP | 设为 `NO` |
| `port_enable` | FTP 可作为对内网端口的跳板 | 设为 `NO` |
| Redis `requirepass` | 未认证客户端可直接访问 Redis | 执行 `CONFIG SET requirepass Manus123` |
| 服务重载 | 修改后不生效 | `sudo /restart-ftp.sh` |

需要特别说明的是，`seccomp_sandbox=YES` 在本环境中会导致 FTP 服务异常，因此它并不是本题最终通过裁判所必需的配置项。[1] 另外，曾将 `/home/ctf/.ash_history` 处理为指向 `/dev/null` 的符号链接，但从裁判脚本来看，这同样不是决定性条件。[1]

## 六、修复后验证与取旗结果

在 Redis 已启用 `requirepass` 且 FTP 匿名登录被禁止后，等待一个判题周期，即可看到 `/flag` 成功生成。终端复核输出显示：错误 Redis 口令返回 `WRONGPASS`，`/home/ctf/.ash_history` 已指向 `/dev/null`，`vsftpd.conf` 中 `anonymous_enable=NO`，并且 `/flag` 文件已经存在且可读。[1] [2]

| 验证项 | 结果 | 说明 |
| --- | --- | --- |
| Redis 错误口令认证 | 返回 `WRONGPASS` | 满足裁判第一阶段条件 |
| FTP 匿名访问 | 已关闭 | 满足裁判第二阶段条件 |
| `/flag` 文件 | 已生成 | 判题认可修复结果 |
| 最终 flag | `xctf{0c8ad26cb1fb4cc4855b73dce8739c8a81fe78f4}` | 题目通过 |

本题最终 flag 如下。

```text
xctf{0c8ad26cb1fb4cc4855b73dce8739c8a81fe78f4}
```

## 七、题目本质总结

这道题的训练重点在于：**不要被表面线索牵着走，而要尽快还原真实判题条件。** 题面中的 Redis 与 FTP 提示都是真线索，但如果只修 FTP，不去核实 Redis 是否也进入裁判逻辑，就会一直停留在“看起来已经加固，却始终不出 flag”的状态。

从攻防对抗角度看，本题实际上在训练一种非常实战化的能力：先从显性风险点入手完成第一轮加固，再通过最小可控的提权面或可观测点去验证后台判题或检查逻辑，最终把修复动作收敛到真正有效的最小集合。最终成功解法并不复杂，但前提是必须先识别出 **Redis requirepass + FTP anonymous disable** 这一组合条件。[1] [2]

## 八、最终答案

本题最终 flag 为：

```text
xctf{0c8ad26cb1fb4cc4855b73dce8739c8a81fe78f4}
```

## References

[1]: ../02-证据与脚本/system_service_hardening_live_findings.md "系统服务加固现场记录"
[2]: ../02-证据与脚本/second_challenge_judge_and_flag.out "第二题裁判逻辑与最终 flag 证据"
[3]: ../02-证据与脚本/ttyd_exec.py "ttyd 终端自动执行脚本"
