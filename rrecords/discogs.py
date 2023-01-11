
from sqlalchemy_get_or_create import get_or_create
from .models.models import (
    User, Artist, Release, Track, FormatDescription, Format,
    unique_field_value
)

from .schemas.schemas import release_w_track_schema, track_schema
from . import db, celery

@celery.task(name='app.discogs.sync_collection')
def sync_collection(user_id, folder):
    user = User.query.get(user_id)
    client = user.open_discogs()
    discogs_collection = client.identity().collection_folders[folder]
    for instance in discogs_collection.releases:
        discogs_release = instance.release
        print(discogs_release.title)
        release = Release.query.filter(Release.discogs_id==discogs_release.id).first()
        if release is None:
            release = add_from_discogs(discogs_release, commit=False)
        if release not in user.collections[folder].releases:
            user.collections[folder].releases.append(release)

        db.session.commit()

def add_from_discogs(discogs_release, commit=False):

    data = release_w_track_schema.load(discogs_release)
    
    if not unique_field_value(Release, 'discogs_id', data['discogs_id']):
        print(f"Already found {data['title']}")
        return

    artists_data = data.pop('artists', None)
    formats_data = data.pop('formats', None)
    release = Release(**data)

    # Create / Find artists, append to .artists list on this release
    if artists_data:
        for artist_data in artists_data:
            artist, _ = get_or_create(db.session, Artist, **artist_data)
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
                    desc, _ = get_or_create(db.session, FormatDescription, **description)
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