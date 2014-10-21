# from scrapy import log, signals
# from scrapy.crawler import Crawler
# from scrapy.utils.project import get_project_settings

# from twisted.internet import reactor

# from scraper.spiders.mangareader import MangaReader


def run_spider(spider, manga, issue, to_mail):
    pass
    # kwargs = {
    #     'manga': manga,
    #     'issue': issue,
    #     'from': None,
    #     'to': to_mail,
    # }

    # spider = MangaReader(**kwargs)
    # settings = get_project_settings()
    # crawler = Crawler(settings)
    # crawler.signals.connect(reactor.stop, signal=signals.spider_closed)
    # crawler.configure()
    # crawler.crawl(spider)
    # crawler.start()
    # log.start()
    # reactor.run()
