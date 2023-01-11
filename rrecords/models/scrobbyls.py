from sqlalchemy import Table, Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship

from marshmallow.validate import Length, Range
from marshmallow_sqlalchemy import SQLAlchemySchema, auto_field
from marshmallow import (
    EXCLUDE, fields,
    pre_dump, post_dump, pre_load, post_load, validates,
    ValidationError
)

from .. import db
from .. import ma

class ReleaseScrobbyl(db.Model):
    __tablename__ = 'release_scrobbyls'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship("User", back_populates="release_scrobbyls")
    release_id = Column(Integer, ForeignKey('releases.id'))
    release = relationship("Release", back_populates="scrobbyls")
    started_at = Column(DateTime)
    ended_at = Column(DateTime)

# class ReleaseScrobbylSchema(ma.SQLAlchemySchema):
#     id = auto_field()
#     user = fields.Nested("UserSchema")
#     release = relationship("Release", back_populates="scrobbyls")
#     started_at = Column(DateTime)
#     ended_at = Column(DateTime)