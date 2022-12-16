# %%


#
import musicbrainzngs as mb
mb.set_useragent("Example music app", "0.1", "http://example.com/music")
# %%

discogs_id = 19768321
discogs_url = f"https://www.discogs.com/release/{discogs_id}"
mbid = mb.browse_urls(discogs_url, includes=['release-rels'])['url']['release-relation-list'][0]['target']
mb_release = mb.get_release_by_id(mbid, includes=['recordings'])
media_data = mb_release['release']['medium-list']
# %%
OR 

mbr = mb.search_releases(release=f"\"{r.title}\"", artist=f"\"{r.artists[0].name}\"", strict=True)
list(filter(lambda x: x['medium-track-count']==len(r.tracks), mbr['release-list']))
 mb.search_releases(release="Revolver", mediums=5, strict=True)

# %%
from rrecords.models import *
u = User.query.first()
dc = app.get_discogs(u)
r = dc.release(12868697)

d = ReleaseSchema().load(r)