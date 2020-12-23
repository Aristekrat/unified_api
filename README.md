Env Variables
=============

- copy `sample.env` to `.env` file and use real values for variables, e.g. api keys, redis credentials etc

- `REDIS_HOST` - redis host. defaults to `localhost`
- `REDIS_PORT` - redis port. defaults to `6379`
- `REDIS_PASSWORD` - redis password
- `REDIS_SSL` - indicates whether redis server has SSL enabled. Value must be set to `true` for using SSL in client. Defaults to `false`
- `DB_HOST` - database host
- `DB_NAME` - database name
- `DB_USER` - database user
- `DB_PASSWORD` - database user password
- `NEWSAPI_API_KEY` - NewsAPI API key
- `GOOGLE_API_KEY` - Google API key which has enabled AMP permissions
- `SENTRY_DSN` - sentry DSN which should be obtained at `sentry.io`

Arguments
=========

- `--env` - must be one of `local` or `prod`. `local` env enables DEBUG logs and also disables sentry reporting
- `--port` - API port. defaults to `8080`
- `--disable-parser` - disable NewsAPI parser. parser is running by default 

Run
===

- Works with python3.7+
- Install requirements: `pip install -r requirements.txt`
- Run local env on port 9000 with disabled parser: `python -m unifiedpost --env=local --port=9000 --disable-parser`
- Run production version on port 8080 with parser enabled: `python -m unifiedpost --env=production`

Docker
======
- run using docker compose:
- `docker-compose -f docker/dev.docker-compose.yml build`
- `docker-compose -f docker/dev.docker-compose.yml up -d`

Swagger
=======

- works only in `local` env at `http://host:port/apidocs