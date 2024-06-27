release: alembic upgrade head
web: gunicorn cleanmail.web.app:app
worker: python -m cleanmail.worker.dispatcher