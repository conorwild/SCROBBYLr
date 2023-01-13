
from sqlalchemy_get_or_create import get_or_create
from .models.base import (
    User, Artist, Release, Track, FormatDescription, Format, Collection,
    unique_field_value
)

from .schemas.base import (
    release_w_track_schema, track_schema, CollectionSchema
)
import click
from .tasks import tasks_bp
from . import db, celery

# @tasks_bp.cli.command('sync_collection')
# @click.argument("user_id")
# @click.argument("collection_id")
@celery.task(name='scrobblyr.discogs.sync_collection', bind=True)
def sync_discogs_collection_task(self, user_id, collection_id):
    local = Collection.query.get(collection_id)
    if not local:
        raise ValueError(f"Collection ID {collection_id} not found.")

    client = User.query.get(user_id).open_discogs()
    remote_collections = client.identity().collection_folders

    remote = [c for c in remote_collections if c.id == local.discogs_id]
    if not remote:
        raise ValueError(f"No matching remote collection found.")
    
    n_releases = remote[0].count
    if n_releases != local.count:
        local.count = n_releases
        db.session.commit()

    discogs_ids = []
    for i, instance in enumerate(remote[0].releases):
        do_commit = False
        discogs_release = instance.release
        release = Release.query.filter(Release.discogs_id==discogs_release.id).first()
        discogs_ids.append(discogs_release.id)

        if release is None:
            release = add_from_discogs(discogs_release, commit=False)
            do_commit = True

        if release not in local.releases:
            local.releases.append(release)
            do_commit = True

        if do_commit:
            db.session.commit()

        self.update_state(
            state='PROGRESS', 
            meta={'progress': i*100.0/n_releases, 'synced': i-1}
        )

    keep_releases = [r for r in local.releases if r.discogs_id in discogs_ids]
    local.releases = keep_releases
    db.session.commit()

@celery.task(name='scrobbylr.discogs.sync_folders')
def sync_folders_task(user_id):
    collection_schema = CollectionSchema()
    client = User.query.get(user_id).open_discogs()
    folders = client.identity().collection_folders
    for folder in folders:
        folder_data = collection_schema.load(folder) | {'user_id': user_id}
        collection, _ = get_or_create(db.session, Collection, **folder_data)
        
    db.session.commit()

def add_from_discogs(discogs_release, commit=False):

    data = release_w_track_schema.load(discogs_release)
    
    if not unique_field_value(Collection, 'discogs_id', data['discogs_id']):
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