# DomainMate Makefile

.PHONY: help install run test clean docker-build docker-run

help:
	@echo "DomainMate Automation"
	@echo "====================="
	@echo "Make commands:"
	@echo "  install      - Create venv and install dependencies"
	@echo "  run          - Run the audit (requires venv)"
	@echo "  demo         - Run the audit in DEMO mode"
	@echo "  docker-build - Build the Docker image"
	@echo "  docker-run   - Run the audit via Docker"
	@echo "  clean        - Remove venv and temp files"

install:
	python3 -m venv venv
	. venv/bin/activate && pip install -r requirements.txt

run:
	. venv/bin/activate && export PYTHONPATH=$$(pwd) && python src/cli.py

demo:
	. venv/bin/activate && export PYTHONPATH=$$(pwd) && python src/cli.py --demo

clean:
	rm -rf venv
	rm -rf __pycache__
	rm -rf src/__pycache__
	rm -rf src/monitors/__pycache__
	rm -rf src/utils/__pycache__
	rm -rf reports/*.html

docker-build:
	docker build -t domainmate:latest .

docker-run:
	docker run --rm -v $$(pwd)/config.yaml:/app/config.yaml -v $$(pwd)/reports:/app/reports domainmate:latest
