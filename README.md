# Don't forget:
```
python3 connection_manager.py
celery -A celery_worker.celery worker --pool=solo --loglevel=info
```