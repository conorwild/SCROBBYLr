import re
from datetime import datetime, timedelta, timezone
from discogs_client.models import PrimaryAPIObject
from marshmallow.validate import Length
from marshmallow_sqlalchemy import auto_field
from marshmallow import (
    EXCLUDE, fields,
    pre_dump, post_dump, pre_load, post_load, validates,
    ValidationError
)

from ..models.base import (
    User, Release, Collection, Artist, Track, Format, FormatDescription
)
from .scrobbyls import(
    ReleaseScrobbyl
)


from .. import ma

class ReleaseScrobbylSchema(ma.SQLAlchemySchema):
    class Meta:
        model = ReleaseScrobbyl

    id = auto_field()
    user = fields.Nested("UserSchema", only=('id', 'name', 'email'))
    release = fields.Nested("ReleaseSchema", only=('title', 'id', 'artists_sort'))
    started_at = fields.AwareDateTime()
    ended_at = fields.AwareDateTime()