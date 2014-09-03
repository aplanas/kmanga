redis-server &
cd kmanga
SCRAPY_SETTINGS_MODULE=scraper.settings python manage.py rqworker
