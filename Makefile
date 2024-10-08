include .env
.EXPORT_ALL_VARIABLES:

DOCKER_BUILDKIT=1
COMPOSE_DOCKER_CLI_BUILD=1

COMPOSE_PROJECT_NAME=fastvapi
NETWORK_NAME=network-fastvapi
REDIS_VOLUME_NAME=redis-fastvapi

_ngrok:
	@rm -f .ngrok.yml
	@sed -e 's/\$$NGROK_TOKEN/$(NGROK_AUTH_TOKEN)/' -e 's/\$$USERNAME/$(NGROK_USERNAME)/' ./config/ngrok.yml.template > .ngrok.yml

init:
	@$(MAKE) stop
	@$(MAKE) _ngrok
	@docker network create $(NETWORK_NAME) > /dev/null
	@docker volume create $(REDIS_VOLUME_NAME) > /dev/null
	$(MAKE) build

build:
	@docker compose -f docker-compose.yml build

build-nocache:
#	@docker run --rm -it -v ./:/code fastvapi-app:latest poetry lock
	@$(MAKE) _ngrok
	@$(MAKE) prune
	@docker compose -f docker-compose.yml build --no-cache

prune:
	docker builder prune --force --all

start:
	@docker compose -f docker-compose.yml -f docker-compose-dev.yml up -d

stop:
	@docker compose -f docker-compose.yml -f docker-compose-dev.yml down

fastapi.bash:
	@docker exec -it fastvapi-fastapi bash

redis.bash:
	@docker exec -it fastvapi-redis bash
