"""
Powered by my smartsearch module (https://github.com/ironman5366/smartsearch)
"""
# Internal imports
from will.core import arguments
from will.core.plugin_handler import *

# External imports
import smartsearch


@subscribe
class Search(Plugin):

    name = "search"
    arguments = [arguments.WolframAPI, arguments.CommandText]

    def check(self, command_obj):
        """
        Determine whether it's a search command
        """
        command = command_obj.text
        if "search" in command_obj.verbs:
            return True
        question_words = [
            "what",
            "when",
            "why",
            "how",
            "who",
            "are",
            "is"
        ]
        first_word = command.split(" ")[0].lower()
        if first_word in question_words:
            return True
        return False

    def exec(self, **kwargs):
        """
        Use smartsearch to get an answer to the query
        """
        query = kwargs["CommandText"]
        wolfram_key = kwargs["WolframAPI"]
        # Build a smartsearch object
        searcher = smartsearch.Searcher({"wolfram": wolfram_key})
        try:
            response_text = searcher.query(query)
            return {
                "data":
                    {
                        "type": "success",
                        "text": response_text,
                        "id": "SEARCH_SUCCESSFUL"
                    }
            }
        except smartsearch.exceptions.AllClientsFailedError:
            return {
                "errors":
                    [{
                        "type": "error",
                        "id": "SEARCH_FAILED",
                        "text": "Couldn't find an answer to query {0}".format(query)
                    }]
            }
