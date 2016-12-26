from os.path import abspath, dirname, join
from wsgiref.simple_server import make_server

import wikihandlers
from web import Application

BASE_ROOT = dirname(abspath(__file__))


class Config:
    BASE_ROOT = BASE_ROOT
    PAGES_DIRECTORY = join(BASE_ROOT, 'pages')
    TEMPLATES_DIRECTORY = join(BASE_ROOT, 'templates')


app = Application()

with make_server('', 8000, app) as httpd:
    print("Serving on port 8000...")
    app.config = Config()
    app.add_handler(r'^/$', wikihandlers.home_handler)
    app.add_handler(r'^/view/(?P<title>[A-Z][A-Za-z0-9]+)$', wikihandlers.view_handler)
    app.add_handler(r'^/edit/(?P<title>[A-Z][A-Za-z0-9]+)$', wikihandlers.edit_handler)
    app.add_handler(r'^/history/(?P<title>[A-Z][A-Za-z0-9]+)$', wikihandlers.history_handler)
    app.add_handler(r'^/assets/(?P<path>[\w\d\/-_.]+)$', wikihandlers.assets_handler)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()
