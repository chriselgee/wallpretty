DOCKER_IMAGE ?= wallpretty:latest
DOCKER_BUILD_ARGS ?=
DOCKER_PORT_FLAGS ?= -p 80:5000
DOCKER_DEVICE_FLAGS ?=

.PHONY: build test run clean help

help:
	@echo "Targets:"
	@echo "  build  - build $(DOCKER_IMAGE) image using Docker"
	@echo "  test   - launch the website inside the image for browser testing"
	@echo "  run    - start python3 app.py in Docker (binds port 5000)"
	@echo "  clean  - remove cached Python build files"

build:
	docker build $(DOCKER_BUILD_ARGS) -t $(DOCKER_IMAGE) .

# Launch the site for browser-based checks; no GPIO devices attached.
test: build
	docker run --rm -it $(DOCKER_PORT_FLAGS) $(DOCKER_IMAGE)

run: build
	docker run --rm -it $(DOCKER_PORT_FLAGS) $(DOCKER_DEVICE_FLAGS) $(DOCKER_IMAGE)

clean:
	@find . -name "*.pyc" -o -name "__pycache__" -print0 |
		xargs -0 rm -rf
