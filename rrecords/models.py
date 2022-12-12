from flask_login import UserMixin
from flask import current_app as app
import discogs_client
from . import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    discogs_token = db.Column(db.String(32))
    discogs_secret = db.Column(db.String(32))
    discogs_account = db.Column(db.String(20))

    def to_dict(self):

        return {
            c.name: getattr(self, c.name) for c in self.__table__.columns
        }

