from flask import (
    Blueprint, render_template, redirect, url_for, request, flash,
    session, current_app as app
)

from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, logout_user
from ..models import User
from .. import db

auth_bp = Blueprint(
    'auth_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

@auth_bp.route('/login')
def login():
    return render_template('login.html')

@auth_bp.route('/login', methods=['POST'])
def login_post():
    email = request.form.get('email')
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password, password):
        flash('Please check your login details and try again.')
        return redirect(url_for('auth_bp.login'))

    session["name"] = user.name+"SESSION"
    login_user(user, remember=remember)
    return redirect(url_for('main_bp.profile'))

@auth_bp.route('/signup')
def signup():
    return render_template('signup.html')

@auth_bp.route('/signup', methods=['POST'])
def signup_post():
    email = request.form.get('email')
    name = request.form.get('name')
    password = request.form.get('password')

    user = User.query.filter_by(email=email).first()
    if user:
        flash(f"Email Address ({email}) already exists")
        return redirect(url_for('auth_bp.signup'))
    
    new_user = User(
        email=email, name=name,
        password=generate_password_hash(password, method='sha256')
    )

    db.session.add(new_user)
    db.session.commit()

    return redirect(url_for('auth_bp.login'))

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main_bp.index'))
