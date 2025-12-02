FROM python:3.11-slim
LABEL maintainer="Chris Elgee"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt ./
RUN python3 -m pip install --no-cache-dir --upgrade pip && \
	python3 -m pip install --no-cache-dir -r requirements.txt

COPY . .

RUN groupadd -r wallpretty && useradd --no-log-init --system -r -g wallpretty wallpretty && \
	chown -R wallpretty:wallpretty /app

USER wallpretty

CMD ["python3", "websocket-quart.py"]
