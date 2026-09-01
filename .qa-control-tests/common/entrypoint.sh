#!/usr/bin/env bash

set -e

# The shared frontend has no Blade templates, but Laravel's view cache command
# still requires the directory to exist.
mkdir -p /var/www/html/resources/views

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
