from flask import flash
from flask_wtf import FlaskForm, Form
from wtforms import (
    StringField, BooleanField, EmailField, PasswordField,
    SelectField, FormField, FieldList, IntegerField
)
from wtforms.validators import (
    InputRequired, Length, Email, ValidationError
)

from ..models.models import User

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
    email = EmailField(
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
        'Email Address', validators=[InputRequired(), Length(max=30), Email()]
    )

    password = PasswordField(
        'Password', validators=[InputRequired(), Length(min=6, max=20)]
    )

    remember = BooleanField('Remember Me')

class TrackForm(Form):
    scrobbyl = BooleanField('Scrobbyl this track?', default=True)
    id = IntegerField()
    position = StringField()
    title = StringField()
    duration_s = IntegerField()
    duration = StringField()
    musicbrainz_url = StringField()
    musicbrainz_description = StringField()

class FormatForm(Form):
    name = StringField()
    qty = IntegerField()
    description_string = StringField()

class DiscForm(Form):
    id = StringField()
    format = FormField(FormatForm)
    tracks = FieldList(FormField(TrackForm))
    
class ScrobbylReleaseForm(FlaskForm):
    __M = [5, 10, 15, 30, 45, 60, 90, 120]
    __offset_vals = [-x for x in __M[::-1]] + [0] +  __M
    __offset_labs = [f"{o} mins ago" for o in __M[::-1]] + ['now'] + [f"in {o} mins" for o in __M]

    t0 = SelectField(u'', choices=['started', 'ended'])
    offset = SelectField(u'', choices=list(zip(__offset_vals, __offset_labs)), coerce=int)

    id = IntegerField('releases.id')
    title = StringField()
    year = StringField()
    artists_sort = StringField()
    cover_image = StringField()
    discs = FieldList(FormField(DiscForm))
    discogs_url = StringField()
    musicbrainz_url = StringField()



