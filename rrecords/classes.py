from discogs_client import Client as DiscogsClient
from discogs_client.exceptions import HTTPError
from json import JSONEncoder, JSONDecoder
import jsonpickle


class DiscogsClient(DiscogsClient):

    def to_json(self):
        return jsonpickle.encode(self)

    def is_logged_in(self):
        try:
            self.identity()
            return True

        except HTTPError:
            return False
        

class CustomJSONEncoder(JSONEncoder):
    """https://stackoverflow.com/questions/42937612/why-must-a-flask-sessions-value-be-json-serializable
    """
    def default(self, obj):
        if isinstance( obj , DiscogsClient):
            return obj.to_json()
        else:
            return JSONEncoder.default(self , obj)


class CustomJSONDecoder(JSONDecoder):
    def __init__(self, *args, **kwargs):
        self.orig_obj_hook = kwargs.pop("object_hook", None)
        super(CustomJSONDecoder, self).__init__(*args,
            object_hook=self.custom_obj_hook, **kwargs)

    def custom_obj_hook(self, dct):
        if 'discogs' in dct:
            try:
                dct['discogs'] = jsonpickle.decode(dct['discogs'])
            except:
                pass

        if (self.orig_obj_hook):
            return self.orig_obj_hook(dct) 

        return dct