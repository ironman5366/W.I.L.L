# Internal imports
from will.core.plugin_handler import *
from will.core import arguments

@subscribe
class News(Plugin):
    name = "news"
    arguments = [arguments.News]

    def exec(self, **kwargs):
        news_str = kwargs["News"]
        return news_str