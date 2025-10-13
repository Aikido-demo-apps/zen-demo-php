#!/usr/bin/env bash

# Ensure resources/views directory exists for view:cache
mkdir -p /var/www/html/resources/views

# Cache config, routes, and views - skip if database not configured
/usr/bin/php /var/www/html/artisan config:cache --no-ansi -q 2>/dev/null || echo "config:cache skipped"
/usr/bin/php /var/www/html/artisan route:cache --no-ansi -q 2>/dev/null || echo "route:cache skipped"
/usr/bin/php /var/www/html/artisan view:cache --no-ansi -q 2>/dev/null || echo "view:cache skipped"
