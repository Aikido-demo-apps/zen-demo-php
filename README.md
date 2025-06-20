# zen-demo-php

## setup

`git submodule update --init --recursive`
copy `.env.example` to `.env`

## run

Test with database
`DATABASE_URL=postgres://username:passowrd@localhost:5432/aikido?sslmode=disable`

docker build -t zen-demo-php:dev .
docker run -p 8080:8080 --env-file .env --name "zen-demo-php" --rm zen-demo-php:dev
