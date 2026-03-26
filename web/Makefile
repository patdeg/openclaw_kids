.PHONY: run build build-arm64 install clean docker-build docker-up docker-down

PORT ?= 8085
BASE_URL ?= http://localhost:8085

run:
	go run *.go -port=$(PORT) -base-url=$(BASE_URL)

build:
	go build -o openclaw-web *.go

build-arm64:
	GOOS=linux GOARCH=arm64 go build -o openclaw-web *.go

clean:
	rm -f openclaw-web

# Docker targets (run from repo root)
docker-build:
	cd .. && docker compose build

docker-up:
	cd .. && docker compose up -d

docker-down:
	cd .. && docker compose down
