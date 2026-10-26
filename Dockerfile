# syntax=docker/dockerfile:1

ARG PHP_VERSION=8.4.27
FROM php:${PHP_VERSION}-fpm-bookworm
LABEL fly_launch_runtime="laravel"

ENV DEBIAN_FRONTEND=noninteractive \
    COMPOSER_ALLOW_SUPERUSER=1 \
    COMPOSER_HOME=/composer \
    COMPOSER_MAX_PARALLEL_HTTP=24 \
    PHP_PM_MAX_CHILDREN=5 \
    PHP_PM_START_SERVERS=2 \
    PHP_MIN_SPARE_SERVERS=1 \
    PHP_MAX_SPARE_SERVERS=3 \
    PHP_DATE_TIMEZONE=UTC \
    PHP_DISPLAY_ERRORS=Off \
    PHP_ERROR_REPORTING=22527 \
    PHP_MEMORY_LIMIT=256M \
    PHP_MAX_EXECUTION_TIME=90 \
    PHP_POST_MAX_SIZE=100M \
    PHP_UPLOAD_MAX_FILE_SIZE=100M \
    PHP_ALLOW_URL_FOPEN=Off

COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl git unzip sqlite3 nginx supervisor cron procps libpq-dev \
    && docker-php-ext-install -j"$(nproc)" pdo_pgsql pgsql \
    && cp "$PHP_INI_DIR/php.ini-production" "$PHP_INI_DIR/php.ini" \
    && mkdir -p /run/php \
    && rm -rf /var/lib/apt/lists/*

COPY .fly/nginx/ /etc/nginx/
# Load after the image's pool settings so our Unix socket and limits take precedence.
COPY .fly/fpm/pool.d/www.conf /usr/local/etc/php-fpm.d/zzz-app.conf
COPY .fly/supervisor/ /etc/supervisor/
COPY .fly/entrypoint.sh /entrypoint
COPY .fly/start-nginx.sh /usr/local/bin/start-nginx
RUN chmod 754 /usr/local/bin/start-nginx

COPY . /var/www/html
COPY resources/public/ /var/www/html/public/
WORKDIR /var/www/html

RUN composer install --optimize-autoloader --no-dev \
    && mkdir -p storage/logs \
    && chown -R www-data:www-data /var/www/html \
    && echo "MAILTO=\"\"\n* * * * * www-data /usr/local/bin/php /var/www/html/artisan schedule:run" > /etc/cron.d/laravel \
    && sed -i='' '/->withMiddleware(function (Middleware \$middleware) {/a\
        \$middleware->trustProxies(at: "*");\
    ' bootstrap/app.php; \
    if [ -d .fly ]; then cp .fly/entrypoint.sh /entrypoint; chmod +x /entrypoint; fi;

ENV AIKIDO_BLOCKING=true

EXPOSE 8080

ENTRYPOINT ["/entrypoint"]
