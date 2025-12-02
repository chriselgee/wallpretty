DOCKER ?= docker
DOCKER_IMAGE ?= wallpretty:latest
PYTHON ?= python3
MODULES ?= websocket-quart.py ws2801_funcs.py test.py letters.py pewpew.py pklite.py
DOCKER_BUILD_ARGS ?=
DOCKER_PORT_FLAGS ?= -p 5000:5000
DOCKER_DEVICE_FLAGS ?=
DOCKER_ENV_FLAGS ?=
DOCKER_MOUNT_FLAGS ?=

.PHONY: build test run clean help

help:
	@echo "Targets:"
	@echo "  build  - build $(DOCKER_IMAGE) image using Docker"
	@echo "  test   - launch the website inside the image for browser testing"
	@echo "  run    - start $(PYTHON) websocket-quart.py in Docker (binds port 5000)"
	@echo "  clean  - remove cached Python build files"

build:
	$(DOCKER) build $(DOCKER_BUILD_ARGS) -t $(DOCKER_IMAGE) .

# Launch the site for browser-based checks; no GPIO devices attached.
test: build
	$(DOCKER) run --rm -it $(DOCKER_PORT_FLAGS) $(DOCKER_ENV_FLAGS) $(DOCKER_MOUNT_FLAGS) $(DOCKER_IMAGE)

run: build
	$(DOCKER) run --rm -it $(DOCKER_PORT_FLAGS) $(DOCKER_DEVICE_FLAGS) $(DOCKER_ENV_FLAGS) $(DOCKER_MOUNT_FLAGS) $(DOCKER_IMAGE)

clean:
	@find . -name "*.pyc" -o -name "__pycache__" -print0 |
		xargs -0 rm -rf
