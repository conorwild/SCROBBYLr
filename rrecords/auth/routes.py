from flask import (
    Blueprint, render_template, redirect, url_for, request, flash,
    session, current_app as app, jsonify
)

from marshmallow.exceptions import ValidationError
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, logout_user
from ..models import User, user_schema, Collection
from .. import db

auth_bp = Blueprint(
    'auth_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

@auth_bp.route('/login')
def login():
    email = request.args.get('email')
    return render_template('login.html', email=email)

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

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        user_data = request.form.to_dict(flat=True)
        try:
            new_user = user_schema.load(user_data)
            new_user.password = generate_password_hash(
                new_user.password, method='sha256'
            )
            new_user.collections.append(Collection())

            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('auth_bp.login', email=new_user.email))

        except ValidationError as errs:
            field = list(errs.messages.keys())[0]
            flash(f"{field.title()}: {errs.messages[field][0]}")

    return render_template('signup.html', code=422)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main_bp.index'))
