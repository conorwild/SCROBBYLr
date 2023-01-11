from .models.models import MusicbrainzRelease
from .schemas.schemas import mb_release_schema
from flask import current_app as app
from musicbrainzngs import ResponseError as MusicBrainzResponseError

from sqlalchemy_get_or_create import get_or_create

import numpy as np

from scipy.optimize import linear_sum_assignment
from thefuzz.process import extractWithoutOrder
from thefuzz.fuzz import ratio

from . import db

_SCALE = 100

def _fuzzy_distance_matrix(v1, v2):
    return np.array([[
        _SCALE-x[1] for x in extractWithoutOrder(item, v2, scorer=ratio)
    ] for item in v1])

def _match_matrix(v1, v2):
    return np.array([[
        v1_item != v2_item for v2_item in v2
    ] for v1_item in v1]) * _SCALE

def _track_distance_matrix(dc_release, mb_release):

    title_distance = _fuzzy_distance_matrix(
        [t.title for t in dc_release.tracks],
        [t.title for t in mb_release.tracks]
    )

    position_match = _match_matrix(
        [t.position for t in dc_release.tracks],
        [t.position for t in mb_release.tracks]
    )

    return (
        0.9 * title_distance + \
        0.1 * position_match
    )


class MusicbrainzNGS():
    import musicbrainzngs as MB

    def __init__(self):
        self.MB.set_useragent(
            app.config['NAME'], 
            app.config['VERSION'], 
            app.config['AUTHOR'],
        )

    def get_release_data(self, mb_release_id):

        if mb_release_id is None:
            return None

        r = self.MB.get_release_by_id(
            mb_release_id,
            includes=['recordings']
        )['release']

        return r
    
    def search_by_url(self, url, **kwargs):
        return self.MB.browse_urls(url, **kwargs)

class MusicbrainzMatcher():

    def __init__(self):
        self._mb = MusicbrainzNGS()

    def match_release_by_url(self, url):
        try: 
            results = self._mb.search_by_url(url, includes=['release-rels'])
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

    def match_release_by_attributes(self, attributes):
        results = self._mb.search_releases(**attributes)
        if results['release-count'] > 0:
            r_idx = 0
            for i, r in enumerate(results['release-list']):
                try:
                    if any(
                        ['vinyl' in ({'format': ''} | r['medium-list'][0])['format'].lower() for f in r['medium-list']]
                    ):
                        r_idx = i
                        break
                except:
                    pass
            return results['release-list'][r_idx]['id']

        return None

    @staticmethod
    def _extract_attributes(release):
        return {
        'release': release.title,
        'artist': release.artists[0].name,
        'date': release.year,
        'mediums': release.n_discs,
        'tracks': release.n_tracks,
    }

    def find_best_matching_release(self, release, threshold_score=90):

        # First, try matching based on the discogs URL
        mb_id = self.match_release_by_url(release.discogs_url)
        if mb_id is not None:
            return (mb_id, 101)

        attributes = self._extract_attributes(release)
        results = self._mb.MB.search_releases(**attributes, strict=False)
        potential_matches = [
            # should probably loop over pages here, we're currently only 
            # looking at the first (best?) 25 items.
            r for r in results['release-list'] if int(r['ext:score']) > threshold_score
        ]
        
        if len(potential_matches) == 0:
            return None

        def has_vinyl(r):
            return any(
                ['vinyl' in ({'format': ''} | f)['format'].lower() for f in r['medium-list']]
            )

        for item in potential_matches:
            if has_vinyl(item) & (item['medium-track-count'] == attributes['tracks']):
                return (item['id'], int(item['ext:score']))

        return (potential_matches[0]['id'], int(potential_matches[0]['ext:score']))
        
    def match_release(self, release):
        id, _code = self.find_best_matching_release(release)
        if id is not None:
            print(f"Found: {release}")
            mb_release_data = mb_release_schema.load(
                self._mb.get_release_data(id)
            )

            mb_release = MusicbrainzRelease.get_or_create(mb_release_data, commit=False)

            release.mb_match = mb_release
            release.mb_match_code = _code

            self.match_tracks(release)

            db.session.commit()
            return True
        return False

    def match_tracks(self, release):
        if release.mb_match is None:
            raise AttributeError(f"{release} must be matched.")
            # Alternatively, could initiate matching here.

        distances = _track_distance_matrix(release, release.mb_match)
        dc_idx, mb_idx = linear_sum_assignment(distances)
        for i in range(len(dc_idx)):
            idc, imb = dc_idx[i], mb_idx[i]
            release.tracks[idc].mb_match = release.mb_match.tracks[imb]
            release.tracks[idc].mb_match_code = distances[idc, imb]



    # @property
    # def mb(self):
    #     return self._mb
