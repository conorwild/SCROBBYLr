from datetime import datetime, timezone
from flask import (
    render_template, session, url_for, abort, request, redirect, flash
)
from flask_login import login_required, current_user

from . import main_bp
from ... import db
from ...models.base import Release, Collection
from ...models.scrobbyls import ReleaseScrobbyl
from ...schemas.base import release_w_disc_schema, collection_schema
from ...forms.forms import ScrobbylReleaseForm
from ...discogs import sync_discogs_collection_task as sync_collection_task
from ...musicbrainz import musicbrainz_match_releases_task as match_releases_task

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

def _taskname(task_fn):
    return task_fn.name[task_fn.name.rindex('.')+1:]

def _task_in_progress(task_fn):
    task_id = session.get(_taskname(task_fn), None)
    if task_id is None:
        return False
    task = task_fn.AsyncResult(task_id)
    if task.state in ['PROGRESS', 'PENDING']:
        return True
    elif task.state in ['SUCCESS']:
        return False
    else:
        raise ValueError(f"Unexpected task state {task.state}")


@main_bp.route('/collection/<id>', methods=["GET"])
@login_required
def collection(id):
    collection = collection_schema.dump([Collection.query.get(id)])[0]
    releases = Collection.query_releases(id, **request.args.to_dict())
    thumbs = [{'id': r.id, 'cover': r.cover_image} for r in releases]
    sync_in_progress = _task_in_progress(sync_collection_task)
    match_in_progress =  _task_in_progress(match_releases_task)
    return render_template(
        'thumbs.html',
        collection=collection, items=thumbs,
        syncing=sync_in_progress, matching=match_in_progress
    )

@main_bp.route('/collection/<id>/update')
@login_required
def update_collection(id):
    task = sync_collection_task.apply_async(args=[current_user.id, id])
    session[_taskname(sync_collection_task)] = task.id
    return redirect(url_for('main_bp.collection', id=id))

@main_bp.route('/collection/<id>/match')
@login_required
def match_collection(id):
    if _task_in_progress(sync_collection_task):
        flash("Please wait for Discogs sync to finish")
    else:
        task = match_releases_task.apply_async(args=[id])
        session[_taskname(match_releases_task)] = task.id
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
        form.timestamp.data = datetime.now(timezone.utc)
        if form.validate_on_submit():
            scrobbyl = ReleaseScrobbyl.from_form(current_user, form)
            db.session.commit()
            return redirect(url_for('main_bp.release', id=id))

@main_bp.route('/admin')
def admin():
    abort(404)
