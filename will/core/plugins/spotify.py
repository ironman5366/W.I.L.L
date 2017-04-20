#Builtin imports
import logging

#External imports
import spotipy
from will.core.plugin_handler import *
from will.core import arguments

sp = spotipy.Spotify()
log = logging.getLogger()

@subscribe
class Spotify(Plugin):

    name = "spotify"
    arguments = [arguments.CommandParsed]

    def exec(self, **kwargs):
        work = None
        event_doc = kwargs["CommandParsed"]
        for chunk in event_doc.noun_chunks:
            # Use dependency parsing to dermine the object of the command
            if chunk.root.dep_ == "dobj":
                work = chunk.text
        if not work:
            return {
                "type": "error",
                "text": "Couldn't parse song from sentence {0}".format(event["command"]),
                "data": {}
            }
        log.debug("In spotify module, found work {0}".format(work))
        song = sp.search(q='track:' + work, type='track')
        # Get the most popular of the found results
        song_items = song["tracks"]["items"]
        pops = {}
        for song_array in song_items:
            song_popularity = song_array["popularity"]
            pops.update({song_popularity: song_array})
        song_item = pops[max(pops.keys())]
        song_data = {
            "name": song_item["name"],
            "popularity": song_item["popularity"],
            "url": song_item["external_urls"]["spotify"],
            "artist": song_item["artists"][0]["name"]
        }
        log.debug("Found song {0}".format(song_data))
        # Get most popular song
        song_str = "Directing you to {0} by {1}".format(song_data["name"], song_data["artist"])
        return {
            "data":
                {
                    "type": "success",
                    "text": song_str,
                    "id": "SPOTIFY_SONG_FOUND"
                },
            "url ": song_data["url"]
        }