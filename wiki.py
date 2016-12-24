import re
from urllib.parse import parse_qs, quote, quote_plus
from wsgiref.simple_server import make_server
from string import Template


class Page:
    title = None
    content = None

    def __init__(self, title, content=None):
        self.title = title
        self.content = content

    def save(self):
        with open(f"{self.title}.rst", 'w') as fileobj:
            fileobj.write(self.content)

    @classmethod
    def load(cls, title: str):
        try:
            with open(f"{title}.rst", 'r+') as fileobj:
                page = cls(title)
                page.content = fileobj.read()
        except IOError:
            return None
        else:
            return page


class Form:
    def __init__(self, environ):
        request_body = environ['wsgi.input'].read().decode()
        self.data = parse_qs(request_body)

    def get(self, key):
        return quote_plus(self.data[key][0])


def redirect(start_response, location):
    start_response("301 OK", [
        ('Location', location),
    ])

    return [b'']


def render_template(template_path, **context):
    with open(template_path, 'r') as fileobj:
        tpl = Template(fileobj.read())

    return tpl.safe_substitute(**context).encode('utf-8')


def handler(environ, start_response):
    page = Page("TestPage", "This is a sample page.")
    page.save()

    start_response("200 OK", [('Content-Type', 'text/plain; charset=utf-8')])
    return [page.content.encode('utf-8')]


def view_handler(environ, start_response):
    title = environ['app.match'].group('title')
    page = Page.load(title)

    if not page:
        return redirect(start_response, f'/edit/{title}')

    start_response("200 OK", [('Content-Type', 'text/html; charset=utf-8')])

    content = render_template('templates/view.html', title=page.title, content=page.content)
    return [content]


def edit_handler(environ, start_response):
    title = environ['app.match'].group('title')
    page = Page.load(title)

    if not page:
        page = Page(title=title, content='')
        page.save()

    if environ['REQUEST_METHOD'] == 'POST':
        form = Form(environ)
        page.title = form.get('title')
        page.content = form.get('content')
        page.save()

        return redirect(start_response, f'/view/{title}')
    else:
        start_response("200 OK", [('Content-Type', 'text/html; charset=utf-8')])

        content = render_template('templates/edit.html', title=page.title, content=page.content)
        return [content]


class Application:
    _handlers = []

    def add_handler(self, path, handler):
        path_pattern = re.compile(path)
        self._handlers.append((path_pattern, handler))

    def __call__(self, environ, start_response):
        for path_pattern, handler in self._handlers:
            match = path_pattern.match(environ['PATH_INFO'])
            if match:
                environ['app.match'] = match
                return handler(environ, start_response)

        start_response("404 OK", [('Content-Type', 'text/plain; charset=utf-8')])
        return [b'Not found']


with make_server('', 8000, Application()) as httpd:
    print("Serving on port 8000...")

    httpd.application.add_handler(r'^/$', handler)
    httpd.application.add_handler(r'^/view/(?P<title>\w+)$', view_handler)
    httpd.application.add_handler(r'^/edit/(?P<title>\w+)$', edit_handler)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()
