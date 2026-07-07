# DomainMate Makefile

.PHONY: help install run demo test clean docker-build docker-run

help:
	@echo "DomainMate Automation"
	@echo "====================="
	@echo "Make commands:"
	@echo "  install      - Create venv and install dependencies"
	@echo "  run          - Run the audit (requires venv)"
	@echo "  demo         - Run the audit in DEMO mode"
	@echo "  test         - Run the test suite"
	@echo "  docker-build - Build the Docker image"
	@echo "  docker-run   - Run the audit via Docker"
	@echo "  clean        - Remove venv and temp files"

install:
	python3 -m venv venv
	. venv/bin/activate && pip install -r requirements.txt pytest

run:
	. venv/bin/activate && export PYTHONPATH=$$(pwd) && python src/cli.py

demo:
	. venv/bin/activate && export PYTHONPATH=$$(pwd) && python src/cli.py --demo

test:
	. venv/bin/activate && export PYTHONPATH=$$(pwd) && pytest -q

clean:
	rm -rf venv
	find . -name __pycache__ -type d -not -path "./venv/*" -exec rm -rf {} +
	rm -rf reports/*.html reports/*.json

docker-build:
	docker build -t domainmate:latest .

docker-run:
	docker run --rm -v $$(pwd)/config.yaml:/app/config.yaml -v $$(pwd)/reports:/app/reports domainmate:latest
