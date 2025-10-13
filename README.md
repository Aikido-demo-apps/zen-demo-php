# zen-demo-php

> :warning: **SECURITY WARNING**
>
> This is a demonstration application that intentionally contains security vulnerabilities for educational purposes.
> - **DO NOT** run this in production environment
> - **DO NOT** run without proper protection
> - It is strongly recommended to use [Aikido Zen](https://www.aikido.dev/zen) as a security layer


## setup

`git submodule update --init --recursive`
copy `.env.example` to `.env`

## run

This application now uses **Apache + mod_php** with a Python control server for management.

### Build and Run

Test with database
`DATABASE_URL=postgres://username:passowrd@localhost:5432/aikido?sslmode=disable`

```bash
docker build -t zen-demo-php:dev .
docker run -p 8080:8080 -p 8081:8081 --env-file .env --name "zen-demo-php" --rm zen-demo-php:dev
```

### Ports

- **8080**: Apache web server (PHP application)
- **8081**: Python control server (Apache management API)

### Control Server

The Python control server provides HTTP endpoints to manage the Apache server:

- `GET /health` - Health check
- `GET /status` - Get Apache status
- `POST /start_server` - Start Apache
- `POST /stop_server` - Stop Apache
- `POST /restart` - Hard restart Apache
- `POST /graceful-restart` - Graceful restart Apache
- `GET /get-server-logs` - Get Apache logs
- `GET /config-test` - Test Apache configuration

#### Quick Start Apache

```bash
# Start Apache
curl -X POST http://localhost:8081/start_server

# Check status
curl http://localhost:8081/status

# Graceful restart
curl -X POST http://localhost:8081/graceful-restart

# Get logs
curl "http://localhost:8081/get-server-logs?type=error&lines=50"
```

#### Testing

Test the control server with the provided scripts:

```bash
# Using bash script
./test_control_server.sh

# Using Python client
./test_control_client.py
```

For detailed API documentation, see [CONTROL_SERVER.md](CONTROL_SERVER.md)
