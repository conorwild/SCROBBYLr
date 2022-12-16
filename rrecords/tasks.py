
from . import celery
from .models import User, Release

from flask import current_app
from flask_login import current_user

@celery.task(name='app.tasks.sync_w_discogs')
def sync_w_discogs(user_id, folder):
    user = User.query.get(user_id)
    user.sync_with_discogs(folder=folder)

