from flask_login import UserMixin
from sqlalchemy.orm import relationship, backref
from marshmallow import fields, pre_dump, pre_load
from marshmallow.validate import Length, Range
from marshmallow_sqlalchemy import SQLAlchemySchema, auto_field
from datetime import datetime

from . import db
from . import ma

class User(UserMixin, db.Model):

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100))
    discogs_token = db.Column(db.String(32))
    discogs_secret = db.Column(db.String(32))
    discogs_account = db.Column(db.String(20))

    created_at = db.Column(
        db.DateTime, server_default=db.func.current_timestamp()
    )

    # releases = relationship("Release", secondary="collections")

    def to_dict(self):
        return {
            c.name: getattr(self, c.name) for c in self.__table__.columns
        }

class UserSchema(ma.SQLAlchemySchema):
    class Meta:
        model = User
        load_instance = True

    @pre_load
    def repl_empty(self, data, **kwargs):
        for field in data:
            data[field] = data[field] or None
        return data

    id = auto_field()
    name = auto_field(required=True, validate=Length(max=20))
    email = fields.Email(required=True, validate=Length(max=50))
    password = auto_field(required=True, validate=Length(min=6, max=20))
    discogs_token = auto_field()
    discogs_secret = auto_field()
    discogs_account = auto_field()

user_schema = UserSchema()

# class Release(db.Model):

#     __tablename__ = 'releases'
#     id = db.Column(db.Integer, primary_key=True)
#     title = db.Column(db.String(255))
#     discogs_id = db.Column(db.Integer, unique=True)
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)

#     users = relationship("User", secondary="collections")

# class Collection(db.Model):
#     __tablename__ = 'collections'
#     id = db.Column(db.Integer, primary_key=True)
#     user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
#     release_id = db.Column(db.Integer, db.ForeignKey('releases.id'))
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)

#     user = relationship(
#         User, backref=backref("collections", cascade="all, delete-orphan")
#     )
    
#     release = relationship(
#         Release, backref=backref("collections", cascade="all, delete-orphan")
#     )