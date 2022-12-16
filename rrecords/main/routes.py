from flask import (
    render_template, current_app as app, url_for, abort, request, redirect
)
from flask_login import login_required, current_user

from . import main_bp
from .. import db
from ..models import Release, release_schema
from ..tasks import sync_w_discogs

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/profile')
@login_required
def profile():

    return render_template(
        'profile.html', 
        dc_connected=app.discogs_logged_in(current_user),
    )

def _validate_folder(folder):
    try:
        folder = int(folder)
        if folder not in range(len(current_user.collections)):
            raise ValueError
    except ValueError:
        abort(422)
    return folder

@main_bp.route('/collection/<folder>', methods=["GET"])
def collection(folder):
    folder = _validate_folder(folder)

    releases = [
        {'title': r.title, 'artist': r.artists_sort} for 
        r in current_user.collections[folder].releases
    ]
    return render_template('collection.html', items=releases)

@main_bp.route('/collection/<folder>/thumbs', methods=["GET"])
def collection_thumbs(folder):
    folder = _validate_folder(folder)
    releases = Release.query_user_folder(
        current_user, folder, **request.args.to_dict()
    )

    thumbs = [{'id': r.id, 'cover': r.cover_image} for r in releases]

    return render_template('thumbs.html', items=thumbs)

@main_bp.route('/collection/<folder>/update')
def update_collection(folder):
    try:
        folder = int(folder)
        if folder not in range(len(current_user.collections)):
            raise ValueError
    except ValueError:
        abort(422)

    sync_w_discogs.apply_async(args=[current_user.id, folder])
    return redirect(url_for('main_bp.collection', folder=folder))

from ..models import ReleaseSchema

@main_bp.route('/release/<id>', methods=["GET", "POST"])
def release(id):
    release = release_schema.dump(Release.query.get(id))
    if request.method == "GET":
        return render_template(
            'release.html', item=release
        )


@main_bp.route('/test')
def test():
    current_user.sync_with_discogs()

@main_bp.route('/admin')
def admin():
    abort(404)
