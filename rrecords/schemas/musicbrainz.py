from marshmallow_sqlalchemy import auto_field
from marshmallow import EXCLUDE, fields, pre_load

from flatdict import FlatDict

from ..models.musicbrainz import  MusicbrainzRelease, MusicbrainzTrack

from .. import ma

class MusicbrainzSchema(ma.SQLAlchemySchema):

    @pre_load()
    def convert_musicbrainz(self, mb_data, **kwargs):
        if 'id' in mb_data:
            mb_data['mb_id'] = mb_data.pop('id')
        return mb_data

class MusicbrainzReleaseSchema(MusicbrainzSchema):

    class Meta:
        model = MusicbrainzRelease
        unknown = EXCLUDE

    @pre_load()
    def extract_tracks(self, mb_data, **kwargs):
        mb_data['tracks'] = [
            t for m in mb_data['medium-list'] for t in m['track-list']
        ]
        return mb_data

    id = auto_field()
    mb_id = auto_field()
    tracks = fields.List(fields.Nested("MusicbrainzTrackSchema"))

class MusicbrainzTrackSchema(MusicbrainzSchema):

    _valid_duration_fields = [
        'length', 'track_or_recording_length', 'recording_length'
    ]

    @pre_load
    def preprocess_track(self, mb_track, **kwargs):
        mb_track = dict(FlatDict(mb_track, delimiter='_'))
        dfield = (
            [k for k in  self._valid_duration_fields if k in mb_track]+[None]
        )[0]
        if dfield is not None:
            secs = int(int(mb_track[dfield])/1000)
            mb_track['duration_s'] = secs
            mb_track['duration'] = f"{secs//60:d}:{secs%60:02d}"
            
        mb_track['title'] = mb_track.pop('recording_title')
        
        # Rename to make it clear this is MB id
        mb_track['recording_mb_id'] = mb_track.pop('recording_id')

        # Swap to make these consitent with Discogs terminology
        mb_track['position'], mb_track['number'] = mb_track['number'], mb_track['position']
        return mb_track

    class Meta:
        model = MusicbrainzTrack
        unknown = EXCLUDE

    id = auto_field()
    mb_id = auto_field()
    title = auto_field()
    position = auto_field()
    number = auto_field()
    duration = auto_field()
    duration_s = auto_field()
    recording_mb_id = auto_field()  

mb_release_schema = MusicbrainzReleaseSchema()
mb_track_schema = MusicbrainzTrackSchema()