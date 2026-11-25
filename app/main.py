"""Small status API used to practise the full CI/CD path:
build -> test -> scan -> push -> deploy to Kubernetes with Helm."""

import logging
import os
import socket
import time

from flask import Flask, jsonify
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

APP_VERSION = os.getenv("APP_VERSION", "dev")
APP_ENV = os.getenv("APP_ENV", "local")

REQUESTS = Counter("status_api_requests_total", "HTTP requests", ["endpoint", "code"])
LATENCY = Histogram("status_api_request_seconds", "Request latency", ["endpoint"])

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='{"ts":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}',
)
log = logging.getLogger("status-api")

_started = time.time()


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        with LATENCY.labels("/").time():
            REQUESTS.labels("/", "200").inc()
            return jsonify(
                service="status-api",
                version=APP_VERSION,
                env=APP_ENV,
                hostname=socket.gethostname(),
            )

    @app.get("/healthz")
    def healthz():
        # liveness: the process is up
        REQUESTS.labels("/healthz", "200").inc()
        return jsonify(status="ok")

    @app.get("/readyz")
    def readyz():
        # readiness: give the app a short warm-up before taking traffic
        ready = time.time() - _started > float(os.getenv("WARMUP_SECONDS", "0"))
        code = 200 if ready else 503
        REQUESTS.labels("/readyz", str(code)).inc()
        return jsonify(ready=ready), code

    @app.get("/metrics")
    def metrics():
        return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}

    log.info("status-api started, version=%s env=%s", APP_VERSION, APP_ENV)
    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
