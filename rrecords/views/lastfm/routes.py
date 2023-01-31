from flask import (
    render_template, redirect, url_for, request, flash,
    session, current_app as app, flash
)

from flask_login import login_required, current_user
# from discogs_client.exceptions import HTTPError

from ...lastfm import (LastFMNetwork, SessionKeyGenerator)

from . import lastfm_bp
from ... import db
# from ...discogs import sync_folders_task

# @app.errorhandler(HTTPError)
# def handle_bad_request(e):
#     flash(f"Discogs HTTPError {e.msg}")
#     return redirect(url_for('main_bp.profile'))

@lastfm_bp.route('login', methods=["GET"])
@login_required
def login():
    print('logging in')
    network = LastFMNetwork(
        app.config['LASTFM_KEY'],
        app.config['LASTFM_SECRET']
    )
    keygen = SessionKeyGenerator(network)

    auth_url = keygen.handshake_web_auth_url(
        url_for('lastfm_bp.auth', _external=True)
    )

    return redirect(auth_url)

@lastfm_bp.route('auth', methods=["GET"])
@login_required
def auth():
    print('Authorizing')
    token = request.args.get('token')
    network = LastFMNetwork(
        app.config['LASTFM_KEY'],
        app.config['LASTFM_SECRET']
    )
    keygen = SessionKeyGenerator(network)
    session_key = keygen.handshake_get_session_key(token)
    
    current_user.lastfm_key = session_key
    db.session.commit()

    return redirect(url_for('main_bp.profile'))
