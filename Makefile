.PHONY: run build build-arm64 clean docker-build docker-up docker-down update

# Delegate Go targets to web/Makefile
run build build-arm64 clean:
	$(MAKE) -C web $@

# Docker targets
docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

# Full update cycle
update:
	./update.sh
