from flask import (
    render_template, current_app as app, url_for, abort, request
)
from flask_login import login_required, current_user

from . import main_bp
from .. import db
from ..models import Release


@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/profile')
@login_required
def profile():

    # current_user.sync_with_discogs()

    return render_template(
        'profile.html', 
        dc_connected=app.discogs_logged_in(current_user),
    )

@main_bp.route('/collection/<folder>', methods=["GET"])
def collection(folder):
    try:
        folder = int(folder)
        if folder not in range(len(current_user.collections)):
            raise ValueError
    except ValueError:
        abort(422)

    releases = [
        {'title': r.title, 'artist': r.artists_sort} for 
        r in current_user.collections[folder].releases
    ]
    return render_template('collection.html', items=releases)
