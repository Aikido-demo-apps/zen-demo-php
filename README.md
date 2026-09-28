# zen-demo-php

> :warning: **SECURITY WARNING**
>
> This is a demonstration application that intentionally contains security vulnerabilities for educational purposes.
> - **DO NOT** run this in production environment
> - **DO NOT** run without proper protection
> - It is strongly recommended to use [Aikido Zen](https://www.aikido.dev/zen) as a security layer


One Laravel app for PHP-FPM, FrankenPHP classic, and FrankenPHP worker mode.
All three use the same routes, dependencies, UI submodule, and firewall version
in `.fly/scripts/aikido.sh`.

## Build

```sh
git submodule update --init --recursive
```

Choose the runtime to build:

```sh
# PHP-FPM with Nginx (default)
docker build -t zen-demo-php:dev .

# FrankenPHP classic
docker build -f Dockerfile.frankenphp --target classic -t zen-demo-php:dev .

# FrankenPHP worker
docker build -f Dockerfile.frankenphp --target worker -t zen-demo-php:dev .
```

FrankenPHP worker mode uses `.fly/frankenphp/worker.php` as its front controller,
including the Aikido request lifecycle hooks and Laravel state cleanup from the
worker demo. The PHP-FPM QA Dockerfiles also use this shared application.

## Run

Copy the example settings:

```sh
cp .env.example .env
```

Set these values in `.env`, replacing existing entries or appending overrides at the end:

- `APP_KEY`: a Laravel base64 encryption key.
- `DATABASE_URL`: the PostgreSQL connection URL.
- `AIKIDO_TOKEN`: the token connecting the demo to Aikido.

Then run:

```sh
docker run -p 8080:8080 --env-file .env --name zen-demo-php --rm zen-demo-php:dev
```

## Deploy

The Fly workflow deploys all existing apps from this repository:

| Runtime | Fly configurations |
| --- | --- |
| PHP-FPM | `fly.toml`, `fly-danger.toml`, `fly-demo.toml` |
| FrankenPHP classic | `fly-frankenphp.toml`, `fly-frankenphp-danger.toml` |
| FrankenPHP worker | `fly-frankenphp-worker.toml`, `fly-frankenphp-worker-danger.toml` |

Deploy an individual app with `flyctl deploy --remote-only --config <file>`.
App names and the danger apps' `AIKIDO_DISABLE=true` setting are preserved.

Before switching deployments here, make sure this repository's `FLY_API_TOKEN`
secret can deploy to all seven Fly apps. Their existing Fly secrets and databases
stay with those apps. Disable the deployment workflows in `zen-demo-frankenphp`
and `zen-demo-frankenphp-worker` when switching so they cannot deploy older copies
over this shared app. Future app and firewall updates belong here.
