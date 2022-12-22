
from . import celery, db
from .models import User, Release
from .musicbrainz import MusicBrainzMatcher as MB
from flask import Blueprint
import click


@celery.task(name='app.tasks.sync_w_discogs')
def sync_w_discogs(user_id, folder):
    user = User.query.get(user_id)
    user.sync_with_discogs(folder=folder)

tasks_bp = Blueprint('tasks', __name__)

@tasks_bp.cli.command('fix_tracklists')
def fix_tracklists():
    """ Fixes release / tracklist info using manual entries. """
    from .data.tracklists import OVERRIDE
    for id, tracklist in OVERRIDE.items():
        release = Release.query.filter(Release.discogs_id==id).first()
        for ix, new_track_data in tracklist.items():
            assert ix in range(release.n_tracks), "Track index out of range"

            track = release.tracks[ix]
            for field, new_value in new_track_data.items():
                setattr(track, field, new_value)
        db.session.commit()

@tasks_bp.cli.command('match_release')
@click.argument("release_id")
def match_release(release_id):
    m = MB()
    r = Release.query.get(release_id)
    m.match_release(r)
    