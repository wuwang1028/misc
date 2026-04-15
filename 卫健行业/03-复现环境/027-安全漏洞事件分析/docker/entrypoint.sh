#!/bin/sh
set -eu

mkdir -p /var/www/html/uploads
chown -R www-data:www-data /var/www/html/uploads
chmod -R 0775 /var/www/html/uploads

if [ ! -f /flag.txt ]; then
  printf 'flag{D6FAKJ4D5dSoJhOlivIno8zI60R9BjJa}\n' > /flag.txt
  chmod 0644 /flag.txt
fi

exec "$@"
