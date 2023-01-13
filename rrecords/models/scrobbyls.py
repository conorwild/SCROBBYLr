import numpy as np
from datetime import datetime, timedelta, timezone
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, asc, desc
from sqlalchemy.orm import relationship
from sqlalchemy.ext.associationproxy import association_proxy

from ..helpers import strfdelta
from .base import Release, User
from .. import db

class TrackScrobbyl(db.Model):
    __tablename__ = 'track_scrobbyls'

    id = Column(Integer, primary_key=True)
    track_id = Column(ForeignKey('tracks.id'))
    release_scrobbyl_id = Column(
        ForeignKey(
            'release_scrobbyls.id', onupdate="CASCADE", ondelete="CASCADE"
        )
    )
    start_time = Column(DateTime)

    track = relationship(
        "Track", back_populates="scrobbyls"
    )
    release_scrobbyl = relationship(
        "ReleaseScrobbyl", back_populates="track_scrobbyls"
    )

    def __repr__(self):
        return (
            f"<TrackScrobbyl id={self.id} "
            f"track={self.track_id} "
            f"release_scrobbyl={self.release_scrobbyl_id} "
            f"({self.start_time.strftime('%Y-%m-%d %H:%M:%S')})>"
        )

class ReleaseScrobbyl(db.Model):
    __tablename__ = 'release_scrobbyls'

    id = Column(Integer, primary_key=True)
    user_id = Column(ForeignKey('users.id'))
    release_id = Column(ForeignKey('releases.id'))
    start_time = Column(DateTime)
    end_time = Column(DateTime)

    user = relationship(
        "User", back_populates="release_scrobbyls"
    )
    release = relationship(
        "Release", back_populates="scrobbyls"
    )
    track_scrobbyls = relationship(
        "TrackScrobbyl", back_populates="release_scrobbyl",
        cascade='all, delete-orphan'
    )

    tracks = association_proxy("track_scrobbyls", "track")

    def __repr__(self):
        return (
            f"<ReleaseScrobbyl id={self.id} ",
            f"user={self.user_id} ",
            f"release={self.release_id} "
            f"({self.start_time.strftime('%Y-%m-%d %H:%M:%S')})>"
        )


    def tz_end_time(self, tz=timezone.utc):
        return self.end_time.replace(tzinfo=tz)


    def is_playing(self):
        return datetime.now(timezone.utc) < self.tz_end_time(timezone.utc)

    @classmethod
    def most_recent(cls, user, release):
        return (
            cls.query
            .filter(cls.user == user)
            .filter(cls.release == release)
            .order_by(desc(cls.end_time))
            .all()
        )

    @classmethod
    def from_form(cls, user, form, commit=True):
        if not isinstance(form, dict):
            form = form.data
        
        tracks = [t for d in form['discs'] for t in d['tracks']]
        
        track_durations = np.array([
            timedelta(seconds=t['duration_s']) for t in tracks
        ])

        time_offset = timedelta(seconds=form['offset'])
        total_duration = track_durations.sum()
        if form['t0'] == "started":
            started = form['timestamp'] + time_offset
            ended = started + total_duration
        elif form['t0'] == "ended":
            ended = form['timestamp'] + time_offset
            started = ended - total_duration

        r_scrobbyl = ReleaseScrobbyl(
            id=None,
            user=user,
            release=Release.query.get(form['id']),
            started_at=started,
            ended_at=ended
        )

        tracks_end = np.cumsum(track_durations)
        tracks_start = np.insert(tracks_end, 0, timedelta(0))[:-1]
        for i, track in enumerate(tracks):
            t_start = started + tracks_start[i]
            t_scrobbyl = TrackScrobbyl(started_at=t_start, track_id=track['id'])
            r_scrobbyl.track_scrobbyls.append(t_scrobbyl)

        db.session.add(r_scrobbyl)
        if commit:
            db.session.commit()

        return r_scrobbyl

    def duration(self, format='%H:%M:%S'):
        return strfdelta(self.ended_at - self.started_at, format)


