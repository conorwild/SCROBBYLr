import re
from discogs_client.models import PrimaryAPIObject
from marshmallow.validate import Length
from marshmallow_sqlalchemy import auto_field
from marshmallow import (
    EXCLUDE, fields,
    pre_dump, post_dump, pre_load, post_load, validates,
    ValidationError
)

from ..models.base import (
    User, Release, Collection, Artist, Track, Format, FormatDescription,
    unique_field_value
)

from .. import ma

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
    collections = fields.List(fields.Nested("CollectionSchema"))

user_schema = UserSchema()

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

class CollectionSchema(DiscogsSchema):
    class Meta:
        model = Collection
        unknown = EXCLUDE

    id = auto_field()
    name = auto_field()
    discogs_id = auto_field()
    resource_url = auto_field()
    count = auto_field()
    n_synced = fields.Integer()
    n_matched = fields.Integer()

collection_schema = CollectionSchema(many=True)

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
        scrobbyl = None

    @post_load
    def clean_artists_names(self, data, **kwargs):
        data['artists_sort'] = _strip_name(data['artists_sort'])
        return data

    id = auto_field()
    title = auto_field()
    artists_sort = auto_field()
    artists = fields.List(fields.Nested("ArtistSchema"))
    formats = fields.Nested("FormatSchema", many=True)
    thumb = auto_field()
    cover_image = auto_field()
    year = auto_field()
    discogs_id = auto_field()
    master_id = auto_field()
    created_at = auto_field()
    discogs_url = fields.Str()
    musicbrainz_url = fields.Str()

class ReleaseWithTracksSchema(ReleaseSchema):
    tracks = fields.List(fields.Nested("TrackSchema"))
 
release_w_track_schema = ReleaseWithTracksSchema()

class ReleaseWithDiscSchema(ReleaseSchema):
    discs = fields.List(fields.Nested("DiscSchema"))
    
release_w_disc_schema = ReleaseWithDiscSchema()

class DiscSchema(ma.Schema):
    id = fields.Str(required=True)
    format = fields.Nested("FormatSchema")
    tracks = fields.List(fields.Nested("TrackSchema"))


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

    @pre_dump
    def merge_mb_data(self, data, **kwargs):
        if (data.duration_s is None) | (data.duration == ''):
            if data.mb_match is not None:
                data.duration = data.mb_match.duration
                data.duration_s = data.mb_match.duration_s

        return data

    id = auto_field()
    position = auto_field()
    type = auto_field()
    title = auto_field()
    duration = auto_field()
    duration_s = auto_field()
    musicbrainz_url = fields.Str()
    musicbrainz_description = fields.Str()

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

    @post_dump(pass_many=True)
    def expand_qty(self, data, **kwargs):
        if kwargs['many']:
            data = [(f_ | {'qty': 1}) for f in data for f_ in [f]*f['qty']]
        return data

    id = auto_field()
    name = auto_field()
    text = auto_field()
    qty = auto_field()
    description_string = fields.Str()
    descriptions = fields.List(fields.Nested("FormatDescriptionSchema"))

