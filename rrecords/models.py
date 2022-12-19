from flask_login import UserMixin
from flask import current_app as app
from sqlalchemy import Table, Column, ForeignKey, Integer, String, DateTime
from sqlalchemy import asc, desc
from sqlalchemy.orm import relationship, declarative_base
from marshmallow import (
    EXCLUDE, fields, pre_dump, pre_load, post_load, validates, ValidationError
)
from discogs_client.models import PrimaryAPIObject
from sqlalchemy_get_or_create import get_or_create
from marshmallow.validate import Length, Range
from marshmallow_sqlalchemy import SQLAlchemySchema, auto_field
from datetime import datetime
import re
from .classes import DiscogsClient

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

format_to_description = Table(
    "format_to_description_associations",
    db.metadata,
    Column("format_id", ForeignKey("formats.id"), primary_key=True),
    Column("format_description_id", ForeignKey("format_descriptions.id"), primary_key=True),
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

    formats = relationship(
        "Format", back_populates="release"
    )

    def __repr__(self):
        return f"<Release(id={self.id}, title='{self.title}, discogs_id={self.discogs_id}'>"

    @classmethod
    def query_user_folder(cls, user, folder, **order_kws):
        _valid_fields = ['title', 'id', 'artists_sort', 'year', 'created_at']
        _valid_directions = ['asc', 'desc']
        ordering = []
        for field, dir in order_kws.items():
            if (field not in _valid_fields) | (dir not in _valid_directions):
                raise ValueError
            ordering.append(eval(dir)(field))

        return (
            cls.query.join(Collection.releases)
            .filter(Collection.folder==folder)
            .join(Collection.user)
            .filter(User.id==user.id)
            .order_by(*ordering)
            .all()
        )

    @classmethod
    def add_from_discogs(cls, discogs_release, commit=False):

        data = release_schema.load(discogs_release)
        
        if not unique_field_value(cls, 'discogs_id', data['discogs_id']):
            print(f"Already found {data['title']}")
            return

        artists_data = data.pop('artists', None)
        formats_data = data.pop('formats', None)
        release = cls(**data)

        # Create / Find artists, append to .artists list on this release
        if artists_data:
            for artist_data in artists_data:
                artist, got_it = get_or_create(db.session, Artist, **artist_data)
                if got_it:
                    release.artists.append(artist)

        # Create each format entry for this release, and append to list
        # Search for existing matching descriptions, if doesn't exist then
        # create it, and attach to the format entry.
        if formats_data:
            for format_data in formats_data:
                descriptions = format_data.pop('descriptions', None)
                format = Format(**format_data)
                if descriptions:
                    for description in descriptions:
                        desc, got_it = get_or_create(db.session, FormatDescription, **description)
                        if got_it:
                            format.descriptions.append(desc)

                release.formats.append(format)

        # Creat the tracks on this release
        for track in discogs_release.tracklist:
            track_data = track_schema.load(track.data)
            if track_data['type'] == 'track':
                new_track = Track(**track_data)
                release.tracks.append(new_track)

        # Add release (and related children) to session, then commit?
        db.session.add(release)
        if commit:
            db.session.commit()

        return release

class Format(db.Model):
    __tablename__ = 'formats'
    id = Column(Integer, primary_key=True)
    name = Column(String(32))
    qty = Column(Integer, nullable=False)
    text = Column(String(255))
    release_id = Column(Integer, ForeignKey('releases.id', onupdate="CASCADE", ondelete="CASCADE"))
    release = relationship("Release", back_populates="formats")
    descriptions = relationship(
        "FormatDescription", secondary=format_to_description,
        back_populates="formats"
    )

    def __repr__(self):
        return f"<Format id={self.id}, qty={self.qty}, name={self.name}>"

class FormatDescription(db.Model):
    __tablename__ = 'format_descriptions'
    id = Column(Integer, primary_key=True)
    text = Column(String(255))
    formats = relationship(
        "Format", secondary=format_to_description,
        back_populates="descriptions"
    )

    def __repr__(self):
        return f"<Desc id={self.id}, text={self.text}>"

class Track(db.Model):
    __tablename__ = 'tracks'
    id = Column(Integer, primary_key=True)
    position = Column(String(16))
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
    folder = Column(Integer, nullable=False)
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

    def open_discogs(self):
        return DiscogsClient(
            'my_user_agent/1.0',
            consumer_key=app.config['DISCOGS_KEY'],
            consumer_secret=app.config['DISCOGS_SECRET'],
            token=self.discogs_token,
            secret=self.discogs_secret
        )

    def logged_into_discogs(self):
        return self.open_discogs().is_logged_in()

    def sync_with_discogs(self, folder=0):
        client = self.open_discogs()
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
    folder = auto_field()
    user = fields.Nested(lambda: UserSchema())

class DiscogsSchema(ma.SQLAlchemySchema):
    
    @pre_load
    def convert_discogs(self, discogs_record, **kwargs):
        # Sometimes needs to be refreshed to make sure data is fetched.
        if issubclass(discogs_record.__class__, PrimaryAPIObject):
            if discogs_record.previous_request is None:
                discogs_record.refresh()
            discogs_record = discogs_record.data.copy()

        # Rename any discog IDs to 'discogs_id' so we can always go backwards.
        if 'id' in discogs_record:
            discogs_record['discogs_id'] = discogs_record.pop('id')

        # Make sure that any string data are stripped of leading/trailing WS.
        for f, d in discogs_record.items():
            if isinstance(d, str):
                discogs_record[f] = d.strip()

        return discogs_record

def _strip_name(string):
    return re.sub(' \(\d+\)$', '', string)

class ArtistSchema(DiscogsSchema):
    class Meta:
        model = Artist
        unknown = EXCLUDE

    @post_load
    def clean_artist_name(self, data, **kwargs):
        data['name'] = _strip_name(data['name'])
        return data

    id = auto_field()
    name = auto_field()
    discogs_id = auto_field()
    resource_url = auto_field()
    thumbnail_url = auto_field()

artist_schema = ArtistSchema()

class ReleaseSchema(DiscogsSchema):
    class Meta:
        model = Release
        unknown = EXCLUDE

    @post_load
    def clean_artists_names(self, data, **kwargs):
        data['artists_sort'] = _strip_name(data['artists_sort'])
        return data

    id = auto_field()
    title = auto_field()
    artists_sort = auto_field()
    artists = fields.List(fields.Nested(lambda: ArtistSchema))
    tracks = fields.List(fields.Nested(lambda: TrackSchema))
    formats = fields.List(fields.Nested(lambda: FormatSchema))
    thumb = auto_field()
    cover_image = auto_field()
    year = auto_field()
    discogs_id = auto_field()
    master_id = auto_field()
    created_at = auto_field()

release_schema = ReleaseSchema()

class TrackSchema(DiscogsSchema):
    class Meta:
        model = Track
        unknown = EXCLUDE

    @pre_load
    def rename_type_field(self, data, **kwargs):
        data['type'] = data.pop('type_')
        return data

    @post_load
    def duration_in_seconds(self, data, **kwargs):
        if re.match('\d+:\d+', data['duration']):
            m, s = data['duration'].split(':')
            data['duration_s'] = int(m)*60 + int(s)
        return data

    id = auto_field()
    position = auto_field()
    type = auto_field()
    title = auto_field()
    duration = auto_field()
    duration_s = auto_field()

track_schema = TrackSchema()

class FormatDescriptionSchema(ma.SQLAlchemySchema):
    class Meta:
        model = FormatDescription

    @pre_load
    def rename_type_field(self, data, **kwargs):
        return {'text': data}

    id = auto_field()
    text = auto_field()

class FormatSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Format

    id = auto_field()
    name = auto_field()
    text = auto_field()
    qty = auto_field()
    descriptions = fields.List(fields.Nested(FormatDescriptionSchema))

format_schema = FormatSchema()



