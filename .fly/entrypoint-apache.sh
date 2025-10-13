#!/usr/bin/env bash

set -e

echo "=========================================="
echo "Starting Laravel Application with Apache"
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

# Ensure Apache log directory exists
mkdir -p /var/log/apache2
chown -R www-data:www-data /var/log/apache2

# Start cron if needed
echo "Starting cron..."
service cron start

# If a command was passed, run it
if [ $# -gt 0 ]; then
    echo "Running command: $@"
    exec "$@"
else
    # Start the Python control server (main process)
    echo "Starting Python Control Server on port 8081..."
    echo "Apache will be controlled via HTTP API"
    echo "=========================================="
    exec python3 /var/www/html/control_server.py
fi

