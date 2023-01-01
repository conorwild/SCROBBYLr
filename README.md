
# Installation
1. Clone the repository.
2. Create a new Python 3 (>3.9?) virtual environment.
3. Install the dependendices: `pip3 install ./requirements.txt`

# Other requirements
1. [Redis server](https://redis.io/docs/getting-started/) for running background tasks.
2. SQLite (will probably switch to MySQL, later).

# Running the application
1. Start a [redis server](https://redis.io/docs/getting-started/). In a separate terminal window: `redis-server.
2. Start the celery worker. In another terminal (in repository root folder): `celery -A celery_worker.celery worker --pool=solo --loglevel=info`
3. Start the flask app in another terminal window: `flask --app rrecords run --host=0.0.0.0 --port=4999`
4. In your browser, go to `http://127.0.0.1:4999`

# Notes
1. To do anything, you need a [Discogs](https://www.discogs.com/) account, and at least one collection containing at least one album. Note, your primary Discogs collection (containing all releases) is number 0.
2. After linking your discogs account, manually hit to `collections/<number>/update` route to sync your collection data. E.g. `http://127.0.0.1:4999/collections/0/update`

# Things it will do, eventually, or are currently in development.
- ✅ Update collections between RRECORDS and Discogs.
- Find best matches in the [Musicbrainz](https://musicbrainz.org/) database for best track metadata (Discogs track metadata is usally incomplete) (WIP)
- Scrobble disc plays to [Last.fm](https://www.last.fm/) (TBD)
- Track other things:
    - play time on your stylus (WIP)
    - cleanings (TBD)
    - individual disc plays (instead of whole releases - useful if you have boxsets) (WIP)
    - generate stats and figures / data dives (TBD).
- ✅ Generate URLs that can be embedded in NFC chips so you can track these things by waving your phone over an LP cover (if you have the NFC chip there.)