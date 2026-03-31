web: cd apps/api && uvicorn main:app --host 0.0.0.0 --port $PORT
worker: cd apps/api && celery -A core.celery_app worker --loglevel=info --concurrency=2
