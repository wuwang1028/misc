# 027 绕过研究记录

## 已检索资料要点

### 1. HackTricks: phar:// deserialization
- 文章明确指出，`file_exists()`、`filesize()`、`fopen()`、`file_get_contents()` 等文件函数都可能在处理 `phar://` 路径时触发 **PHAR 元数据反序列化**。
- 资料还强调，攻击者常把 PHAR 伪装成 JPG 头，以绕过上传白名单或仅后缀校验。
- 这与当前题目完全吻合：`file.php?c=phar://...` 中的 `file_exists($fpath)` 就是触发点。

### 2. Pentest-Tools: How to exploit the PHAR deserialization vulnerability
- 文章确认 `phar://` 只能针对本地文件起作用，关键在于：
  1. 攻击者可控一个本地文件路径；
  2. 应用调用了可触发解析的文件函数；
  3. 程序作用域内存在可利用的 POP 链。
- 文章提供的是通用 POP/RCE 框架，但没有直接给出“路径包含关键字黑名单”这一场景下的万能绕过。

## 与本题源码的映射

### 已确认源码点
- `file.php` 只做：`require_once('xxxx.php'); $fpath = $_GET['c']; if(file_exists($fpath)) ...`
- `xxxx.php` 中：
  - `Show::__wakeup()` 仅过滤 `gopher|phar|http|file|ftp|dict|..`，过滤的是 `Show->source`，不是 `Action->path`。
  - `Action::isPathValid()` 中，当 `id=1` 时会执行 `include($this->path)`。
  - 但若 `strpos($this->path, 'uploads') !== false`，则直接 `Invalid path, access denied`。

### 当前约束的实际含义
- 不能直接把 `path` 设成 `uploads/xxxx.jpg`，因此“上传 webshell 后再包含上传文件”被题目主动拦住。
- 由于是 `include($this->path)`，理论上仍可尝试：
  1. **包含非 uploads 目录中的可控文件**；
  2. **包含日志、session、临时文件、源码或根目录 flag 文件**；
  3. 利用包装器或符号路径技巧，把真实文件指向 uploads 但字符串本身不出现 `uploads`。

## 初步可疑绕过方向

### A. 路径别名 / 目录穿越替代字符串
- 如果校验只检查字符串中是否出现 `uploads`，则可能尝试：
  - 符号链接；
  - 大小写差异（本题 Linux 下通常无效，且字符串检查区分大小写）；
  - 路径规范化差异，如软链接目录名不含 `uploads`；
  - 其他挂载路径、工作目录相对路径别名。
- 但在当前题面里，攻击者尚未发现能在站点根目录下创建“指向 uploads 的非 uploads 名称链接”的原语，因此暂时只是理论方向。

### B. 包含日志 / session / 临时文件
- 若可控制日志内容或 session 内容，再借 `include()` 执行其中 PHP 代码，就可转 RCE。
- 已实测常见 OpenResty/Nginx 访问日志路径不存在或无法被成功包含。
- 后续仍可继续枚举：PHP session 保存目录、临时上传目录、框架缓存目录。

### C. 直接转向读 flag 而非 RCE
- 因为 `include()` 不仅能执行 PHP，也会把纯文本文件内容直接输出。
- 如果 flag 位于根目录某个纯文本文件，或位于根目录 PHP 文件中的变量/常量里，则可通过当前链直接读取。
- 当前用户提示“flag 在根目录”，因此这条方向优先级最高。

## 当前阶段判断
- 类似案例说明：**PHAR 反序列化本身可以成为 RCE 起点**，但是否能 RCE，取决于 POP 链最终是否落在可执行 sink 上，以及路径控制是否还能命中可执行内容。
- 这题的 POP 链 sink 是 `include($this->path)`，已经很强，但又被 `uploads` 关键字拦截削弱。
- 因此更现实的下一步是：
  1. 继续枚举根目录真实 flag 文件名；
  2. 读取更多源码确认是否存在 session、缓存或日志型二次落点；
  3. 再评估是否有非 uploads 路径上的可控 PHP 内容可被包含。

## 新增资料补充

### 3. PayloadsAllTheThings: File Inclusion / LFI-to-RCE
这组资料把本地文件包含进一步提升到代码执行的常见路线整理得很系统，核心包括：**上传文件自包含**、**日志投毒**、**`/proc/self/environ`**、**PHP session 文件**、**临时上传文件竞争**、**`/proc/*/fd`**、以及 **PEAR/pearcmd.php** 等技巧。对当前题目的价值在于，它给出了一个明确筛选框架：如果“上传文件自包含”被 `uploads` 字符串黑名单挡住，那么就要优先转向 **非 uploads 路径上的可控文件**。

结合本题已恢复的源码，这些路径需要重新排序。由于 `Action::isPathValid()` 只拦截路径字符串中出现 `uploads` 的情况，因此若目标服务器上存在 **session 文件**、**日志文件**、**PHP 临时上传文件**、**`/proc/self/environ`** 或其他可控内容，而且这些路径本身不含 `uploads`，理论上就仍有机会被 `include()`，从而把当前链条提升为 RCE。

## 结合本题得到的更具体假设

| 路线 | 与本题的匹配度 | 当前判断 |
|---|---|---|
| 上传 webshell 后直接包含上传路径 | 低 | 已被 `uploads` 关键字拦截，常规方式不可行 |
| 访问日志投毒后包含日志 | 中 | 已尝试常见 Nginx/OpenResty 日志，暂未命中，但仍可补充枚举 Apache/PHP-FPM 相关路径 |
| `include('/proc/self/environ')` 利用 User-Agent 注入 | 中高 | 路径不含 `uploads`，且往往在容器/单进程环境中较有机会命中，值得专门验证 |
| PHP session 文件包含 | 中高 | 若应用使用原生 PHP session 存储到磁盘，且我们可控部分 session 内容，则可能转成 RCE |
| PHP 临时上传文件竞争 | 中 | 若 `upload.php` 在处理期间存在可竞争窗口，可尝试包含 `/tmp/phpXXXXXX` |
| `pearcmd.php` / 预装开发组件利用 | 中 | 若站点运行在常见 PHP Docker 镜像中，`/usr/local/lib/php/pearcmd.php` 可能存在，值得读文件确认 |
| 继续直接读根目录 flag | 高 | 当前题面已有“flag 在根目录”提示，这仍然是最短路径 |

## 暂时结论

从类似案例来看，**绕过并非没有方向**，但本题最关键的现实问题不是“PHAR 能不能触发”，而是“在 `include($path)` 这一 sink 之后，能否找到一个**不含 uploads 字符串、又能被我们控制为 PHP 代码**的本地文件”。如果找不到这样的文件，链条就更适合拿来**读源码、读配置、读 flag**，而不是稳定打成命令执行。
