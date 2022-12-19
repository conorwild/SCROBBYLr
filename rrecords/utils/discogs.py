import re
track_re = re.compile('(?P<t>\d+)$')
media_re = re.compile('^(?P<m>[a-zA-Z0-9]+)(?=-?\d+$)')
def split_position(position):

    track_m = re.search(track_re, position)    
    if not track_m:
        raise ValueError(f"Invalid track position {position}??")
    else: 
        track = int(track_m.groups('t')[0])

    media_m = re.search(media_re, position)
    if not media_m:
        media = None
    else:
        media = media_m.groups('m')[0]

    return (media, track)
