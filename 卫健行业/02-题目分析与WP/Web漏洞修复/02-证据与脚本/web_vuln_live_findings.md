# Web漏洞修复现场记录

## 当前已确认事实

| 项目 | 结果 |
| --- | --- |
| ttyd 登录方式 | 浏览器终端中使用 `ctf/ctf` 成功登录 |
| 当前用户 | `ctf` |
| 当前目录 | `/home/ctf` |
| `/home/ctf/README.md` | 已读取，题面要求下载并修复 `java-upload-fix-1.0-SNAPSHOT.jar`，修复后将 JAR 放回 `/home/ctf/java-upload-fix-1.0-SNAPSHOT.jar`，再执行 `sudo /restart-web.sh` |
| `/home/ctf` 现状 | 不存在 `java-upload-fix-1.0-SNAPSHOT.jar`，仅见 `README.md`、`.ash_history`、`jartmp*.tmp`、`webvuln_small_test.txt` |
| 运行中服务 | `java -jar /opt/app/java-upload-fix-1.0-SNAPSHOT.jar` 由 root 运行 |
| Web 服务端口 | 本地 `curl http://127.0.0.1:8080/` 返回上传表单页面；`127.0.0.1:80` 不通 |
| 上传表单特征 | 首页包含 `multipart/form-data` 表单，字段名为 `file`，提交按钮文案为“提交” |
| `/restart-web.sh` 逻辑 | 若 `/home/ctf/java-upload-fix-1.0-SNAPSHOT.jar` 存在，则删除 `/opt/app/*`，复制该 JAR 至 `/opt/app/`，设置权限后以 `nohup java -jar /opt/app/java-upload-fix-1.0-SNAPSHOT.jar` 启动 |
| sudo 能力 | `ctf` 仅允许 `NOPASSWD: /restart-web.sh`；`sudo -l` 需输入密码 `ctf` 后可见；不能执行其他 sudo 命令 |
| 受限项 | 无法直接读取 `/root/check/judge.py`，也无法用 sudo 从 `/opt/app` 复制现有 JAR 到 `/home/ctf` |

## 直接摘录

> README 关键信息：
>
> 1. 用 `sz /home/ctf/java-upload-fix-1.0-SNAPSHOT.jar` 可下载文件。
> 2. 下载 JAR 包后，本地分析并修补（不破坏原有业务逻辑）。
> 3. 修复时优先围绕文件控制不足问题，不必命中全部业务细节。
> 4. 修好后放回 `/home/ctf/java-upload-fix-1.0-SNAPSHOT.jar`。
> 5. 执行 `sudo /restart-web.sh` 重启服务。
> 6. 判题约每 15 秒检查一次，成功后生成 `/flag`。

## 下一步建议

需要继续识别应用的具体上传与下载接口，确认是否存在路径穿越/任意路径写入，并尝试通过现有应用能力导出自身 JAR、重建修复版 JAR，或直接构造最小兼容修复版应用后上传重启。

## 2026-04-15 补充确认

| 项目 | 结果 |
| --- | --- |
| 真实上传接口 | `GET /` 返回的表单 `action` 为 `/doUpload` |
| 上传测试 | 使用 `abc.txt` 与 `../../tmp/poc.txt` 调用 `/doUpload` 均得到 `HTTP/1.1 200` 且响应体为 `nonono` |
| 结论 | 当前接口至少存在额外的后缀、内容或文件名校验，不能直接用普通文本或裸路径穿越文件名完成写入 |
| 终端自动化 | 已创建 `/home/ubuntu/ttyd_exec.py`，可稳定获取远端纯文本输出，后续可继续用它批量探测规则与验证修复 |
| 旧本地材料状态 | 交接文档中提到的 `webvuln_fixed_project/` 等文件在当前沙箱未找到，说明需要重新获取原始 JAR 或重新重建项目 |
| 浏览器取包尝试 | 直接在浏览器终端触发 `sz /opt/app/java-upload-fix-1.0-SNAPSHOT.jar` 暂未在本地 `Downloads/` 中看到文件 |

当前最关键的问题已变为：**先获取原始 JAR，或充分还原上传控制逻辑后重建一个兼容的修复版 JAR**。
