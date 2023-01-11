from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy_get_or_create import get_or_create

from .. import db

class MusicbrainzRelease(db.Model):
    __tablename__ = 'mb_releases'
    id = Column(Integer, primary_key=True)
    mb_id = Column(String(36))
    matches = relationship("Release", back_populates="mb_match")

    tracks = relationship(
        "MusicbrainzTrack", back_populates="mb_release",
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f"<mbRelease {self.id}>"

    @classmethod
    def get_or_create(cls, release_data, commit=True):
        tracks_data = release_data.pop('tracks', None)
        mb_release, is_new = get_or_create(db.session, cls, **release_data)

        if is_new:
            for track_data in tracks_data:
                mb_track, _ = get_or_create(
                    db.session, MusicbrainzTrack, **track_data
                )
                mb_release.tracks.append(mb_track)

        db.session.add(mb_release)

        if commit:
            db.session.commit()

        return mb_release

class MusicbrainzTrack(db.Model):
    __tablename__ = 'mb_tracks'
    id = Column(Integer, primary_key=True)
    mb_id = Column(String(36))
    mb_release_id = Column(Integer, ForeignKey('mb_releases.id'))
    mb_release = relationship("MusicbrainzRelease", back_populates="tracks")
    title = Column(String(255))
    position = Column(String(16))
    number = Column(Integer())
    duration = Column(String(16))
    duration_s = Column(Integer)
    recording_mb_id = Column(String(36))
    matches = relationship("Track", back_populates="mb_match")

    def __repr__(self):
        return f"<mbTrack {self.id} title=\"{self.title}\" pos=\"{self.position}\">"