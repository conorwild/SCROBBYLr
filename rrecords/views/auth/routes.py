from . import auth_bp
from flask import (
    render_template, redirect, url_for, flash,
    request, session, current_app as app,
)
from marshmallow.exceptions import ValidationError
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, logout_user

from ...models.base import User, Collection
from ...schemas.base import user_schema
from ...forms.forms import UserRegistrationForm, UserLoginForm, flash_errors

from ... import db

# @auth_bp.route('/login')
# def login():
#     email = request.args.get('email')
#     return render_template('login.html', email=email)

@auth_bp.route('/login', methods=['POST', 'GET'])
def login():
    form = UserLoginForm(email=request.args.get('email'))
    if request.method == "POST":
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

    return render_template('login.html', form=form)

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    form = UserRegistrationForm()
    if request.method == 'POST':

        if form.validate_on_submit():
            user_data = {
                f:v for f,v in form.data.items() if f not in ['csrf_token']
            }
            new_user = user_schema.load(user_data)
            new_user.password = generate_password_hash(
                new_user.password, method='sha256'
            )
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('auth_bp.login', email=new_user.email))

        else:
            flash_errors(form)

    return render_template('signup.html', form=form, code=422)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main_bp.index'))
