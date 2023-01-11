from flask import Blueprint

main_bp = Blueprint(
    'main_bp', __name__,
    static_url_path='/main/static',
    template_folder='templates',
    static_folder='static'
)

from . import routes