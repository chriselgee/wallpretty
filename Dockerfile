#Docker image for testing self-destruct
# docker build --force-rm -t wallpretty . && docker run --rm -it -p5000:5000 -e "width=10" wallpretty
FROM python:3.7
MAINTAINER "Chris Elgee"

RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get update && \
apt-get -y --no-install-recommends install \
python3-pip

RUN python3 -m pip install quart RPi.GPIO adafruit-ws2801

RUN useradd -m dockwiz

RUN pwd
RUN ls -l /home/

COPY *py /home/dockwiz/
RUN mkdir /home/dockwiz/templates/
COPY templates/index.html /home/dockwiz/templates/

RUN chown -R dockwiz: /home/dockwiz/

USER dockwiz
WORKDIR /home/dockwiz/

CMD ["python3","./websocket-quart.py"]
