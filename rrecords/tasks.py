from .models.base import User, Release
from flask import Blueprint
import click

from . import celery, db

tasks_bp = Blueprint('tasks', __name__)

@tasks_bp.cli.command('fix_releases')
def fix_releases():
    """ Fixes release / tracklist info using manual entries. """
    from .data.releases import OVERRIDE
    for id, new_rl_data in OVERRIDE.items():
        release = Release.query.filter(Release.discogs_id==id).first()
        new_track_data = new_rl_data.pop('tracks', None)
        for field, new_value in new_rl_data.items():
            setattr(release, field, new_value)

        if new_track_data is not None:
            for ix, new_track_data in new_track_data.items():
                try:
                    assert ix in range(release.n_tracks), "Track index out of range"
                    track = release.tracks[ix]
                    for field, new_value in new_track_data.items():
                        setattr(track, field, new_value)
                except AssertionError:
                    print("WARNING: SOMETHING")

        db.session.commit()

    