from .models import Release
from flask import current_app as app
from musicbrainzngs import ResponseError as MusicBrainzResponseError
from . import db

class MusicBrainzMatcher():
    import musicbrainzngs as mb

    def __init__(self):
        self.mb.set_useragent(
            app.config['NAME'], 
            app.config['VERSION'], 
            app.config['AUTHOR'],
        )

    def match_release_by_url(self, url):

        try: 
            results = self.mb.browse_urls(url, includes=['release-rels'])
        except MusicBrainzResponseError:
            return None

        if results is None:
            return None
        
        results = results['url']['release-relation-list']
        if len(results) > 1:
            print(f"WARNING: Multiple URL matches for {url}; taking first.")
            # insert logic to test the various matches and select best
            results = [results[0]] # for now, take first

        return results[0]['release']['id']

    def match_release_by_attributes(self, release):

        return None

    def _attempt_release_matching_strategies(self, release):
        mb_id = self.match_release_by_url(release.discogs_url)
        if mb_id is not None: return mb_id 
            
        return None
        
    def match_release(self, release):
        id = self._attempt_release_matching_strategies(release)
        if id is not None:
            release.musicbrainz_id = id
            db.session.commit()
            return True
        return False

    # @property
    # def mb(self):
    #     return self.mb
