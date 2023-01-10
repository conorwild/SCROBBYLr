from flask import flash
from flask_wtf import FlaskForm
from wtforms import (
    StringField, IntegerField, BooleanField, EmailField, PasswordField
)
from wtforms.validators import (
    InputRequired, Length, Email, ValidationError
)

from .models import User

def flash_errors(form):
    """ Flashes form errors
    https://stackoverflow.com/questions/13585663/flask-wtfform-flash-does-not-display-errors
    """

    for field, errors in form.errors.items():
        for error in errors:
            flash(u"Error in the %s field - %s" % (
                getattr(form, field).label.text,
                error
            ), 'error')

class UniqueValue(object):
    def __init__(self, field, message=None):
        self.field = field
        self.message = message or u'already in use'

    def __call__(self, form, field):
        value = field.data
        if User.query.filter_by(**{self.field: field.data}).first():
            raise ValidationError('already in use.')

class UserRegistrationForm(FlaskForm):
    email = StringField(
        'Email Address', validators=[
            InputRequired(), Length(max=30), Email(), UniqueValue(field='email')
        ]
    )

    name = StringField(
        'Name', validators=[
            InputRequired(), Length(max=20), UniqueValue(field='name')
        ]
    )

    password = PasswordField(
        'Password', validators=[InputRequired(), Length(min=6, max=20)]
    )

class UserLoginForm(FlaskForm):

    email = StringField(
        'Email Address', validators=[
            InputRequired(), Length(max=30), Email()
        ]
    )

    password = PasswordField(
        'Password', validators=[InputRequired(), Length(min=6, max=20)]
    )

    remember = BooleanField('Remember Me')