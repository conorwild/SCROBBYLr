#/bin/sh
celery -A celery_worker.celery worker --pool=solo --loglevel=info