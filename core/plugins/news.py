#Internal imports
from core.plugin_handler import subscribe
import tools
#External imports
import newspaper
#Builtin imports
import logging
import threading
import time

log = logging.getLogger()

def is_news(event):
    '''Determine whether to read the news'''
    event_words = [token.orth_.lower() for token in event["doc"]]
    return "news" in event_words

@subscribe({"name": "news", "check": is_news})
def news_reader(event):
    '''Use the excellent newspaper module to fetch the news from the readers favorite site'''
    response = {"type": "success", "text": None, "data": {}}
    db = event['db']
    event_user = event['username']
    user_table = db['users'].find_one(username=event_user)
    user_news_site = user_table["news_site"]
    news_table = db["news"]
    cached_sites = [list(site.values())[0] for site in db.query("SELECT site from `news`")]
    log.debug("Cached sites are {0}".format(cached_sites))
    if user_news_site in cached_sites:
        site_row = news_table.find_one(site=user_news_site)
        site_time = site_row["time"]
        if time.time()<site_time+43200:
            log.info("Using cached news for site {0}".format(user_news_site))
            news_str = site_row["news_str"]
            response["text"] = news_str
    log.info("Parsing news site {0} for user {1}".format(user_news_site, event_user))
    site_object = newspaper.build(user_news_site, memoize_articles=False)
    log.debug("Finished building newspaper object")
    top_articles = site_object.articles[0:4]
    log.debug("Top articles are {0}".format(list(top_articles)))
    output_strs = []
    #Use multithreading to build the objects for the articles
    def build_article_object(article_url):
        '''Build a formatted string with the article title, summary, and url'''
        log.debug("Building article object for article {0}".format(article_url))
        article = newspaper.Article(article_url)
        log.debug("Downloading article {0}".format(article_url))
        article.download()
        log.debug("Finished downloading article {0}, parsing".format(article_url))
        article.parse()
        log.debug("Finished debugging {0}, running nlp".format(article_url))
        article.nlp()
        article_str = "{0} ({1})\n{2}\n".format(
            article.title.encode('ascii', 'ignore'), article_url, article.summary)
        output_strs.append(article_str)
    article_threads = []
    for article in top_articles:
        article_thread = threading.Thread(target=build_article_object, args=(article.url, ))
        article_threads.append(article_thread)
    [thread.start() for thread in article_threads]
    log.debug("Started news parsing threads, waiting for parsing to finish")
    [thread.join() for thread in article_threads]
    log.debug("Compiling article output {0} into string".format(output_strs))
    output_str = '\n'.join(output_strs)
    log.debug("Returning output string {0}".format(output_str))
    db["news"].upsert(dict(site=user_news_site,time=time.time(),news_str=output_str), ['site'])
    response["text"] = output_str
    return response