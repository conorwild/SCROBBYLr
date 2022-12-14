from flask_login import UserMixin
from sqlalchemy.orm import relationship, backref
from marshmallow import fields, pre_dump, pre_load, validates, ValidationError
from marshmallow.validate import Length, Range
from marshmallow_sqlalchemy import SQLAlchemySchema, auto_field
from datetime import datetime

from . import db
from . import ma


class Collection(db.Model):
    __tablename__ = 'collections'
    id = db.Column(db.Integer, primary_key=True)
    note = db.Column(db.String(length=255), nullable=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id', onupdate="CASCADE", ondelete="CASCADE"))
    user = relationship("User", back_populates="collections")


class User(UserMixin, db.Model):

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    discogs_token = db.Column(db.String(32))
    discogs_secret = db.Column(db.String(32))
    discogs_account = db.Column(db.String(20))
    created_at = db.Column(
        db.DateTime, server_default=db.func.current_timestamp()
    )

    collections = db.relationship(
        "Collection", back_populates="user", cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f"<User(id={self.id}, name='{self.name}', email='{self.email}'"

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

    def unique_field_value(self, field, value):
        return User.query.filter(getattr(User, field)==value).first() is None

    @validates("name")
    def unique_name(self, name):
        if not self.unique_field_value('name', name):
            raise ValidationError("already in use.")

    @validates("email")
    def unique_email(self, email):
        if not self.unique_field_value('email', email):
            raise ValidationError("already in use.")

    id = auto_field()
    name = auto_field(required=True, validate=[Length(max=20)])
    email = fields.Email(required=True, validate=Length(max=50))
    password = auto_field(required=True, validate=Length(min=6, max=20))
    discogs_token = auto_field()
    discogs_secret = auto_field()
    discogs_account = auto_field()
    collections = fields.List(fields.Nested(lambda: CollectionSchema))

user_schema = UserSchema()

class CollectionSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Collection
    note = auto_field()
    user = fields.Nested(lambda: UserSchema())



# class User:
    

# class Release(db.Model):
#     __tablename__ = 'releases'
#     id = db.Column(db.Integer, primary_key=True)
#     title = db.Column(db.String(255))
#     thumb = db.Column(db.String(255))
#     cover_image = db.Column(db.String(255))
#     year = db.Column(db.Integer)
#     discogs_id = db.Column(db.Integer, unique=True, nullable=False)
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # users = db.relationship("User", secondary="collections", back_populates="releases")


# class ReleaseSchema(ma.SQLAlchemySchema):
#     collections = fields.Nested(CollectionSchema, many=True)





