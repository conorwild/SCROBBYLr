from discogs_client.exceptions import HTTPError
import discogs_client

def get_discogs(self, user):
    return self.connection_manager.get_discogs_client(user.to_dict())

def close_discogs(self, user):
    self.connection_manager.close_discogs_client(user.to_dict())

def discogs_logged_in(self, user):
    client = self.get_discogs(user)
    try:
        client.identity()
    except HTTPError:
        return False
    return True

def register_discogs_functions(app):

    app.connection_manager.register('get_discogs_client')
    app.connection_manager.register('close_discogs_client')

    app.get_discogs = get_discogs.__get__(app)
    app.close_discogs = close_discogs.__get__(app)
    app.discogs_logged_in = discogs_logged_in.__get__(app)


