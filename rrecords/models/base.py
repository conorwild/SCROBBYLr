from flask_login import UserMixin
from flask import current_app as app

from sqlalchemy import (
    Table, Column, ForeignKey, Integer, String, DateTime,
    asc, desc
)

from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from ..base import DiscogsClient
from itertools import accumulate

from datetime import datetime
import re

from .. import db

def unique_field_value(model, field, value):
    return model.query.filter(getattr(model, field)==value).first() is None

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
    mb_match_id = Column(Integer, ForeignKey('mb_releases.id'))
    mb_match = relationship("MusicbrainzRelease", back_populates="matches")
    mb_match_code = Column(Integer)
    scrobbyls = relationship("ReleaseScrobbyl", back_populates="release")

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
        return f"<Release id={self.id}, title='{self.title}, discogs_id={self.discogs_id}'>"

    @hybrid_property
    def n_tracks(self):
        return len(self.tracks)

    @property
    def n_discs(self):
        valid_formats = Format._vinyl_names + Format._other_names
        return sum(
            [f.qty for f in self.formats if f.name in valid_formats]
        )

    @property
    def discs(self):
        return self._assign_tracks_to_discs()

    @property
    def discogs_url(self):
        return f"https://www.discogs.com/release/{self.discogs_id}"

    @property
    def musicbrainz_url(self):
        if self.mb_match is None:
            return None
        return f"https://musicbrainz.org/release/{self.mb_match.mb_id}"

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

    @property
    def vinyl_tracks(self):
        return [track for track in self.tracks if track.is_on_vinyl]

    @property
    def nonvinyl_tracks(self):
        return [track for track in self.tracks if not track.is_on_vinyl]

    def _assign_tracks_to_discs(self):

        vinyl_discs = []
        vinyl_ids = [track.disc_id for track in self.vinyl_tracks]
        vinyl_formats = [
            f_ for f in self.formats for f_ in [f]*f.qty if f_.name in Format._vinyl_names
        ]

        side_idxs = accumulate(
            [vinyl_ids[i] != vinyl_ids[i-1] for i in range(len(vinyl_ids))]
        )
        disc_idxs = [(side-1)// 2 for side in list(side_idxs)]

        for t_idx, d_idx in enumerate(disc_idxs):
            if d_idx >= len(vinyl_discs):
                vinyl_discs.append({
                    'id': f"LP{d_idx+1}",
                    'format': vinyl_formats[d_idx] if d_idx < len(vinyl_formats) else None,
                    'tracks': [],
                })
            vinyl_discs[d_idx]['tracks'].append(self.vinyl_tracks[t_idx])

        other_discs = {}
        other_formats = [
            f_ for f in self.formats for f_ in [f]*f.qty if f_.name in Format._other_names
        ]
        for t in self.nonvinyl_tracks:
            other_discs.setdefault(t.disc_id, []).append(t)

        other_discs = [{
            'id': d_id,
            'format': other_formats[d_idx] if d_idx < len(other_formats) else None,
            'tracks': tracks,
        } for d_idx, (d_id, tracks) in enumerate(other_discs.items())]

        return vinyl_discs + other_discs
        

class Format(db.Model):
    __tablename__ = 'formats'
    id = Column(Integer, primary_key=True)
    name = Column(String(32))
    qty = Column(Integer, nullable=False)
    text = Column(String(255))
    release_id = Column(
        Integer, 
        ForeignKey('releases.id', onupdate="CASCADE", ondelete="CASCADE")
    )
    release = relationship("Release", back_populates="formats")
    descriptions = relationship(
        "FormatDescription", secondary=format_to_description,
        back_populates="formats"
    )

    _vinyl_names = ['Vinyl']
    _other_names = ['CD', 'DVD']

    def __repr__(self):
        return f"<Format id={self.id}, qty={self.qty}, name={self.name}>"

    @property
    def description_string(self):
        return ", ".join(
            filter(None, [self.text]+[d.text for d in self.descriptions])
        ) or None

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

    release_id = Column(
        Integer, 
        ForeignKey('releases.id', onupdate="CASCADE", ondelete="CASCADE")
    )
    release = relationship("Release", back_populates="tracks")

    mb_match_id = Column(Integer, ForeignKey('mb_tracks.id'))
    mb_match = relationship("MusicbrainzTrack", back_populates="matches")
    mb_match_code = Column(Integer)

    def __repr__(self):
        return f"<Track(position='{self.position}', title='{self.title}')>"

    _track_re = re.compile(r'(?P<t>\d+)$')
    _disc_re = re.compile(r'^(LP-)?(?P<m>[a-zA-Z0-9]+)')
    _vinyl_disc_re = re.compile(r'^([a-zA-Z])\1*$')

    @property
    def track_number(self):
        m = re.search(self._track_re, self.position)    
        if m is None:
            return -1
        return int(m.groups('t')[0])

    @property
    def disc_id(self):
        m1 = re.search(self._track_re, self.position)
        m2 = re.match(self._disc_re, self.position[:None if m1 is None else m1.span()[0]])
        if m2 is None:
            return "?"
        return m2.groups()[-1]
        
    @property
    def disc_track_position(self):
        return (self.disc_id, self.track_number)

    @property
    def is_on_vinyl(self):
        try:
            return re.match(self._vinyl_disc_re, self.disc_id) is not None
        except:
            pass

    @property
    def musicbrainz_url(self):
        if self.mb_match is None:
            return None
        return f"https://musicbrainz.org/track/{self.mb_match.mb_id}"

    @property
    def musicbrainz_description(self):
        if self.mb_match is None:
            return None
        mb = self.mb_match
        return f"{mb.position} - {mb.title} ({mb.duration})"

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
    user_id = Column(
        Integer,
        ForeignKey('users.id', onupdate="CASCADE", ondelete="CASCADE")
    )
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
    release_scrobbyls = relationship("ReleaseScrobbyl", back_populates="user")

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






