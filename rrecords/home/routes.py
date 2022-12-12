from flask import Blueprint, render_template, current_app as app, url_for, request
from flask_login import login_required, current_user

from .. import db

main_bp = Blueprint(
    'main_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

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
