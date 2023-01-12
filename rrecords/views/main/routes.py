from datetime import datetime, timezone
from flask import (
    render_template, current_app as app, url_for, abort, request, redirect
)
from flask_login import login_required, current_user

from . import main_bp
from ... import db
from ...models.base import Release, Collection
from ...models.scrobbyls import ReleaseScrobbyl
from ...schemas.base import release_w_disc_schema, collection_schema
from ...forms.forms import ScrobbylReleaseForm
from ...discogs import sync_collection


@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/profile')
@login_required
def profile():
    return render_template(
        'profile.html', 
        dc_connected=current_user.logged_into_discogs(),
    )

@main_bp.route('/collections', methods=["GET"])
@login_required
def collections():
    collections = collection_schema.dump(current_user.collections)
    return render_template('collections.html', collections=collections)

def _validate_folder(folder):
    try:
        folder = int(folder)
        if folder not in range(len(current_user.collections)):
            raise ValueError
    except ValueError:
        abort(422)
    return folder

@main_bp.route('/collection/<id>', methods=["GET"])
@login_required
def collection(id):
    releases = Collection.query_releases(id, **request.args.to_dict())

    thumbs = [{'id': r.id, 'cover': r.cover_image} for r in releases]

    return render_template('thumbs.html', items=thumbs)

@main_bp.route('/collection/<id>/update')
@login_required
def update_collection(id):
    sync_collection.apply_async(args=[current_user.id, id])
    return redirect(url_for('main_bp.collection', id=id))

@main_bp.route('/release/<id>', methods=["GET", "POST"])
@login_required
def release(id):
    release = release_w_disc_schema.dump(Release.query.get(id))
    form = ScrobbylReleaseForm(**release, offset=0)
    if request.method == "GET":
        return render_template(
            'release.html', form=form
        )
    elif request.method == "POST":
        if form.validate_on_submit():

            return redirect(url_for('main_bp.release', id=id))

@main_bp.route('/test')
@login_required
def test():
    dc = current_user.open_discogs()
    rr = dc.release(24971641)
    Release.add_from_discogs(rr)

@main_bp.route('/admin')
def admin():
    abort(404)
