#!/usr/bin/env bash

set -e

echo "=========================================="
echo "Starting Laravel Application with Nginx + PHP-FPM"
echo "=========================================="

# Run user scripts, if they exist (includes migrations.sh)
if [ -d /var/www/html/.fly/scripts ]; then
    for f in /var/www/html/.fly/scripts/*.sh; do
        if [ -f "$f" ]; then
            echo "Running script: $f"
            bash "$f"
        fi
    done
fi

# Copy frontend resources to public directory
echo "Copying frontend resources..."
if [ -d /var/www/html/resources/public ]; then
    cp -r /var/www/html/resources/public/* /var/www/html/public/ 2>/dev/null || true
fi
if [ -f /var/www/html/resources/index.html ]; then
    cp -f /var/www/html/resources/*.html /var/www/html/public/ 2>/dev/null || true
fi

# Set proper permissions
echo "Setting permissions..."
chown -R www-data:www-data /var/www/html
chown -R www-data:www-data /var/www/html/storage
chown -R www-data:www-data /var/www/html/bootstrap/cache

# Ensure Nginx and PHP-FPM log directories exist
mkdir -p /var/log/nginx
mkdir -p /var/run/php
chown -R www-data:www-data /var/log/nginx
chown -R www-data:www-data /var/run/php

# Start cron if needed
echo "Starting cron..."
service cron start

# Replace environment variable placeholders in PHP-FPM pool config
echo "Configuring PHP-FPM environment variables..."
sed -i "s|__AIKIDO_BLOCKING__|${AIKIDO_BLOCKING:-false}|g" /etc/php/8.2/fpm/pool.d/www.conf
sed -i "s|__AIKIDO_BLOCK__|${AIKIDO_BLOCK:-false}|g" /etc/php/8.2/fpm/pool.d/www.conf
sed -i "s|__AIKIDO_DISK_LOGS__|${AIKIDO_DISK_LOGS:-false}|g" /etc/php/8.2/fpm/pool.d/www.conf
sed -i "s|__AIKIDO_DEBUG__|${AIKIDO_DEBUG:-false}|g" /etc/php/8.2/fpm/pool.d/www.conf
sed -i "s|__AIKIDO_TOKEN__|${AIKIDO_TOKEN:-}|g" /etc/php/8.2/fpm/pool.d/www.conf
sed -i "s|__AIKIDO_ENDPOINT__|${AIKIDO_ENDPOINT:-https://guard.aikido.dev/}|g" /etc/php/8.2/fpm/pool.d/www.conf
sed -i "s|__AIKIDO_REALTIME_ENDPOINT__|${AIKIDO_REALTIME_ENDPOINT:-https://runtime.aikido.dev/}|g" /etc/php/8.2/fpm/pool.d/www.conf

# If a command was passed, run it
if [ $# -gt 0 ]; then
    echo "Running command: $@"
    exec "$@"
else
    # Start the Python control server (main process)
    echo "Starting Python Control Server on port 8081..."
    echo "Nginx and PHP-FPM will be controlled via HTTP API"
    echo "=========================================="
    exec python3 /var/www/html/control_server.py
fi

