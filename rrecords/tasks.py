
from . import celery
from .models import User


@celery.task(name='app.tasks.sync_w_discogs')
def sync_w_discogs(user_id, folder):
    user = User.query.get(user_id)
    user.sync_with_discogs(folder=folder)

