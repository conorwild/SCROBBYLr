from flask import Blueprint

discogs_bp = Blueprint(
    'discogs_bp', __name__, url_prefix='/discogs',
    template_folder='templates',
    static_folder='static'
)

from . import routes