from flask import (
    render_template, redirect, url_for, request, flash,
    session, current_app as app, flash
)

from flask_login import login_required, current_user
from discogs_client.exceptions import HTTPError

from . import discogs_bp
from ... import db
from ...discogs import sync_folders_task

@app.errorhandler(HTTPError)
def handle_bad_request(e):
    flash(f"Discogs HTTPError {e.msg}")
    return redirect(url_for('main_bp.profile'))

@discogs_bp.route('login', methods=["GET"])
@login_required
def login():
    print('logging in')
    client = current_user.open_discogs()
    _, _, auth_url = client.get_authorize_url(
        url_for('discogs_bp.auth', _external=True)
    )
    session['discogs'] = client
    return redirect(auth_url)

@discogs_bp.route('auth', methods=["GET"])
@login_required
def auth():
    verifier = request.args.get('oauth_verifier')
    client = session.pop('discogs')

    token, secret = client.get_access_token(verifier)
    current_user.discogs_token = token
    current_user.discogs_secret = secret
    current_user.discogs_account = client.identity().username
    db.session.commit()

    return redirect(url_for('discogs_bp.sync_folders'))

@discogs_bp.route('sync_folders', methods=['GET'])
@login_required
def sync_folders():
    sync_folders_task(current_user.id)
    return redirect(url_for('main_bp.collections'))

@discogs_bp.route('logout', methods=["GET"])
@login_required
def logout():
    current_user.discogs_token = None
    current_user.discogs_secret = None
    current_user.discogs_account = None
    db.session.commit()

    return redirect(url_for('main_bp.profile'))