from flask import Blueprint

lastfm_bp = Blueprint(
    'lastfm_bp', __name__, url_prefix='/lastfm',
    template_folder='templates',
    static_folder='static'
)

from . import routes