#!/usr/bin/env bash

set -e

for script in /var/www/html/.fly/scripts/*.sh; do
    if [ -f "$script" ]; then
        bash "$script" -e
    fi
done

chown -R www-data:www-data \
    /var/www/html/storage \
    /var/www/html/bootstrap/cache \
    /var/www/html/database
mkdir -p /run/php /var/log/apache2 /var/log/nginx
service cron start

if [ "$#" -gt 0 ]; then
    exec "$@"
fi

exec python3 /usr/local/bin/control-server
