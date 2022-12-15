from flask_login import UserMixin
from flask import current_app as app
from sqlalchemy import Table, Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship, declarative_base
from marshmallow import fields, pre_dump, pre_load, validates, ValidationError
from marshmallow.validate import Length, Range
from marshmallow_sqlalchemy import SQLAlchemySchema, auto_field
from datetime import datetime
import re

from . import db
from . import ma

Base = declarative_base()

release_to_collection = Table(
    "release_to_collection_associations",
    db.metadata,
    Column("collection_id", ForeignKey("collections.id"), primary_key=True),
    Column("release_id", ForeignKey("releases.id"), primary_key=True),
)

artist_to_release = Table(
     "artist_to_release_associations",
    db.metadata,
    Column("artist_id", ForeignKey("artists.id"), primary_key=True),
    Column("release_id", ForeignKey("releases.id"), primary_key=True),
)

class Release(db.Model):
    __tablename__ = 'releases'
    id = Column(Integer, primary_key=True)
    title = Column(String(255))
    artists_sort = Column(String(255))
    thumb = Column(String(255))
    cover_image = Column(String(255))
    year = Column(Integer)
    discogs_id = Column(Integer, unique=True, nullable=False)
    master_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    collections = relationship(
        "Collection", secondary=release_to_collection,
        back_populates="releases"
    )

    artists = relationship(
        "Artist", secondary=artist_to_release,
        back_populates="releases"
    )

    tracks = relationship(
        "Track", back_populates="release", cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f"<Release(id={self.id}, title='{self.title}, discogs_id={self.discogs_id}'>"

    @classmethod
    def add_from_discogs(cls, discogs_release, commit=False):
        if 'master_id' not in discogs_release.data:
            discogs_release.refresh()

        data = ReleaseSchema().dump(discogs_release.data)
        if not unique_field_value(cls, 'discogs_id', data['discogs_id']):
            print(f"Already found {data['title']}")
            return

        artists_data = data.pop('artists')
        release = cls(**data)
        for artist_data in artists_data:
            artist = Artist.query.filter(Artist.discogs_id==artist_data['discogs_id']).first()
            if artist is None:
                artist = Artist(**artist_data)
            release.artists.append(artist)

        for track in discogs_release.tracklist:
            track_data = TrackSchema().dump(track.data)
            if track_data['type'] == 'track':
                new_track = Track(**track_data)
                release.tracks.append(new_track)

        db.session.add(release)
        if commit:
            db.session.commit()

        return release

# c
# r = dc.release(16038490)

class Track(db.Model):
    __tablename__ = 'tracks'
    id = Column(Integer, primary_key=True)
    position = Column(String(8))
    type = Column(String(32))
    title = Column(String(128))
    duration = Column(String(16))
    duration_s = Column(Integer)

    release_id = Column(Integer, ForeignKey('releases.id', onupdate="CASCADE", ondelete="CASCADE"))
    release = relationship("Release", back_populates="tracks")

    def __repr__(self):
        return f"<Track(position='{self.position}', title='{self.title}'>"

class Artist(db.Model):
    __tablename__ = 'artists'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    discogs_id = Column(Integer, nullable=False, unique=True)
    resource_url = Column(String(255))
    thumbnail_url = Column(String(255))

    releases = relationship(
        "Release", secondary=artist_to_release,
        back_populates="artists"
    )

    def __repr__(self):
        return f"<Artist(id={self.id}, name='{self.name}, discogs_id={self.discogs_id}'>"

class Collection(db.Model):
    __tablename__ = 'collections'
    id = Column(Integer, primary_key=True)
    note = Column(String(length=255), nullable=True)

    user_id = Column(Integer, ForeignKey('users.id', onupdate="CASCADE", ondelete="CASCADE"))
    user = relationship("User", back_populates="collections")

    releases = relationship(
        "Release", secondary=release_to_collection,
        back_populates="collections"
    )

class User(UserMixin, db.Model):

    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String(20), nullable=False)
    email = Column(String(50), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    discogs_token = Column(String(32))
    discogs_secret = Column(String(32))
    discogs_account = Column(String(20))
    created_at = Column(
        DateTime, server_default=db.func.current_timestamp()
    )

    collections = relationship(
        "Collection", back_populates="user", cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f"<User(id={self.id}, name='{self.name}', email='{self.email}'>"

    def to_dict(self):
        return {
            c.name: getattr(self, c.name) for c in self.__table__.columns
        }

    def sync_with_discogs(self, folder=0):
        client = app.get_discogs(self)
        discogs_collection = client.identity().collection_folders[folder]
        for instance in discogs_collection.releases:
            discogs_release = instance.release
            print(discogs_release.title)
            release = Release.query.filter(Release.discogs_id==discogs_release.id).first()
            if release is None:
                release = Release.add_from_discogs(discogs_release, commit=False)
            if release not in self.collections[folder].releases:
                self.collections[folder].releases.append(release)

        db.session.commit()

def unique_field_value(model, field, value):
    return model.query.filter(getattr(model, field)==value).first() is None

class UserSchema(ma.SQLAlchemySchema):
    class Meta:
        model = User
        load_instance = True

    @pre_load
    def repl_empty(self, data, **kwargs):
        for field in data:
            data[field] = data[field] or None
        return data

    @validates("name")
    def unique_name(self, name):
        if not unique_field_value(User, 'name', name):
            raise ValidationError("already in use.")

    @validates("email")
    def unique_email(self, email):
        if not unique_field_value(User, 'email', email):
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

class ArtistSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Artist

    @pre_dump
    def remap_id(self, data, **kwargs):
        data['discogs_id'] = data.pop('id')
        return data

    id = auto_field()
    name = auto_field()
    discogs_id = auto_field()
    resource_url = auto_field()
    thumbnail_url = auto_field()

class ReleaseSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Release

    @pre_dump
    def remap_id(self, data, **kwargs):
        data['discogs_id'] = data.pop('id')
        return data

    id = auto_field()
    title = auto_field()
    artists_sort = auto_field()
    artists = fields.List(fields.Nested(lambda: ArtistSchema))
    tracks = fields.List(fields.Nested(lambda: TrackSchema))
    thumb = auto_field()
    cover_image = auto_field()
    year = auto_field()
    discogs_id = auto_field()
    master_id = auto_field()
    created_at = auto_field()
    
class TrackSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Track

    @pre_dump
    def duration_in_seconds(self, data, **kwargs):
        if re.match('\d+:\d+', data['duration']):
            m, s = data['duration'].split(':')
            data['duration_s'] = int(m)*60 + int(s)
        return data

    @pre_dump
    def remap_type(self, data, **kwargs):
        data['type'] = data.pop('type_')
        return data

    id = auto_field()
    position = auto_field()
    type = auto_field()
    title = auto_field()
    duration = auto_field()
    duration_s = auto_field()





