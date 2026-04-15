mysql -uroot -proot -e "ALTER USER 'root'@'localhost' IDENTIFIED BY 'Xctf2026Db_9'; DROP DATABASE test; DROP USER 'root'@'%'; FLUSH PRIVILEGES;" 2>&1

echo '=== verify new root ==='
mysql -uroot -p'Xctf2026Db_9' -Nse "select user,host,plugin from mysql.user; show databases;" 2>&1

echo '=== flag ==='
ls -l /flag 2>/dev/null
cat /flag 2>/dev/null
