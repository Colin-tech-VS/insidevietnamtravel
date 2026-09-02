"""Configuration Gunicorn pour Scalingo (équivalent nginx côté process web).

Bind $PORT, un worker (mémoire container S), threads pour le concurrent,
timeout long pour l'admin. Les sondes /api/health et /healthz restent hors DB.
"""

import os

bind = f"0.0.0.0:{os.environ.get('PORT', '5002')}"
workers = int(os.environ.get("WEB_CONCURRENCY", "1"))
threads = int(os.environ.get("GUNICORN_THREADS", "4"))
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "120"))
graceful_timeout = 30
keepalive = 5
preload_app = True
forwarded_allow_ips = "*"
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOGLEVEL", "info")
