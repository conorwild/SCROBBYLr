# import atexit
from multiprocessing import Lock
from multiprocessing.managers import BaseManager

from werkzeug.utils import import_string
from flask.config import Config
from discogs_client import Client as DClient
import os

from config import Config


discog_connections = {}
lock = Lock()

def has_discogs_client(user):
    return user['id'] in discog_connections

def get_discogs_client(user):
    with lock:
        if user['id'] not in discog_connections:
            print(f"Creating new DClient for {user['name']}")
            discog_connections[user['id']] = DClient(
                'my_user_agent/1.0',
                consumer_key=Config.DISCOGS_KEY,
                consumer_secret=Config.DISCOGS_SECRET,
                token=user['discogs_token'],
                secret=user['discogs_secret']
            )

        return discog_connections[user['id']]

def close_discogs_client(user):
    with lock:
        if user['id'] in discog_connections:
            print(f"Closing DClient for {user['name']}")
            del discog_connections[user['id']]

manager = BaseManager(
    ('', Config.CONNECTION_MGR_PORT), Config.CONNECTION_MGR_SECRET
)

manager.register('has_discogs_client', has_discogs_client)
manager.register('get_discogs_client', get_discogs_client)
manager.register('close_discogs_client', close_discogs_client)

server = manager.get_server()
server.serve_forever()