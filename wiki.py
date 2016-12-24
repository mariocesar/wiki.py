import contextlib
import io
import os
import re
import string
from urllib.parse import parse_qs, unquote_plus
from wsgiref.handlers import format_date_time
from wsgiref.simple_server import make_server


# Classes

class Page:
    def __init__(self, title, content=None):
        self.title = title
        self.content = content

    @classmethod
    def load(cls, title: str):
        try:
            with open(f"pages/{title}.txt", 'r+') as fileobj:
                page = cls(title)
                page.content = fileobj.read()
        except IOError:
            return None
        else:
            return page

    def save(self):
        with open(f"pages/{self.title}.txt", 'w') as fileobj:
            fileobj.write(self.content)


class Form:
    def __init__(self, environ):
        self.environ = environ

        try:
            content_length = int(environ.get('CONTENT_LENGTH', 0))
        except ValueError:
            content_length = 0

        stream = (environ['wsgi.input']
                  .read(content_length)
                  .decode())

        self.data = parse_qs(stream)

    def get(self, key):
        value = self.data[key][0]
        value = unquote_plus(value)
        return escape(value)


# Utils

def redirect(start_response, location):
    """Shortcut to return a redirect response."""
    start_response("302 OK", [('Location', location)])

    return [b'']


def render_template(template_path, **context):
    """Render a string using a file as template and the given context."""
    with open(template_path, 'r') as fileobj:
        tpl = string.Template(fileobj.read())

    return tpl.safe_substitute(**context)


def template_response(start_response, template_path, context, status=200):
    """Shortcut to return an html response using a template."""
    start_response(f"{status} OK", [
        ('Content-Type', 'text/html; charset=utf-8')
    ])

    content = render_template(template_path, **context)

    return [content.encode('utf-8')]


def text_response(start_response, content, status=200):
    """Shortcut to return a text/plain response."""
    start_response(f"{status} OK", [
        ('Content-Type', 'text/plain; charset=utf-8')
    ])

    return [content.encode()]


def fileobj_response(start_response, path):
    """Shortcut to return a text/plain response."""

    try:
        with open(path, 'rb') as fobj:
            fs = os.fstat(fobj.fileno())  # Get file size

            start_response(f"200 OK", [
                ('Content-Type', 'application/octet-stream'),
                ('Content-Length', str(fs[6])),
                ('Last-Modified', format_date_time(fs[8]))
            ])

            data = fobj.read(1024)

            while data:
                yield data
                data = fobj.read(1024)
    except OSError:
        return text_response(start_response, 'File not found', status=404)


def escape(value):
    """Replace special characters to return a safe sequence."""
    return (value
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', "&quot;"))


def wiki_text(value):
    """Renders text using a basic wiki syntax."""

    value = escape(value)

    # Redirects all print output to a buffer variable `output`
    with io.StringIO() as output, contextlib.redirect_stdout(output):

        inside_pre_block = False

        for chunk in value.split('\n'):
            chunk = chunk.strip()

            if inside_pre_block:
                if chunk.startswith('```'):
                    # Close the preformatted block and set the state to false.
                    inside_pre_block = False
                    print('</pre>')
                    continue

                else:
                    # Do not process the chunk if you are still inside a
                    # preformatted block, just return it as it is.

                    print(chunk)
                    continue

            if chunk.startswith('#'):
                # Extracts level and text from the text

                match = re.match('^(?P<level>[#]+)?\s*(?P<text>.*)', chunk)
                level = len(match.group('level'))
                text = match.group('text')

                print(f'<h{level}>{text}</h{level}>')

            elif chunk.startswith('```'):
                # Start preformatted block

                inside_pre_block = True
                print('<pre>')

            else:
                # Linkify. Search for the form [CamelCase] and
                # wraps a link on every ocurrence.
                chunk_with_links = re.sub(
                    r'\[([A-Z]\w+)\]',
                    r'<a href="/view/\1">\1</a> ',
                    chunk)

                # Paragraph
                print(f'<p>{chunk_with_links}</p>')

        return output.getvalue()


# Handlers

def home_handler(environ, start_response):
    """The main handler, just redirects to the default wiki Page."""
    return redirect(start_response, '/view/Home')


def view_handler(environ, start_response):
    """View handler loads and render the given wiki Page."""
    title = environ['app.match'].group('title')

    page = Page.load(title)

    if not page:
        return redirect(start_response, f'/edit/{title}')

    context = {'title': escape(page.title),
               'content': wiki_text(page.content)}

    return template_response(start_response, 'templates/view.html', context)


def edit_handler(environ, start_response):
    """Edit a wiki Page, if the page doesn't exists it will create it."""
    title = environ['app.match'].group('title')
    page = Page.load(title)

    if not page:
        page = Page(title=title)
        page.content = ''

    if environ['REQUEST_METHOD'] == 'POST':
        form = Form(environ)

        page.title = form.get('title')
        page.content = form.get('content')
        page.save()

        return redirect(start_response, f'/view/{title}')
    else:

        return template_response(
            start_response, 'templates/edit.html',
            {'title': page.title, 'content': page.content})


def assets_handler(environ, start_response):
    """Serves all found files in the assets directory."""
    path = environ['app.match'].group('path')
    path = os.path.join('assets/', path)

    if os.path.isfile(path):
        return fileobj_response(start_response, path)

    return text_response(start_response, 'File Not found', status=404)


class WebApp:
    _handlers = []

    def add_handler(self, urlpattern, handler):
        """Register a handler to later resolve by matching the url pattern."""
        urlpattern = re.compile(urlpattern)
        self._handlers.append((urlpattern, handler))

    def __call__(self, environ, start_response):
        for urlpattern, handler in self._handlers:
            match = urlpattern.match(environ.get('PATH_INFO', ''))

            if match:
                environ['app.match'] = match
                return handler(environ, start_response)

        return text_response(start_response, 'Not found', status=404)


app = WebApp()

with make_server('', 8000, app) as httpd:
    print("Serving on port 8000...")

    app.add_handler(r'^/$', home_handler)
    app.add_handler(r'^/view/(?P<title>[A-Z][A-Za-z0-9]+)$', view_handler)
    app.add_handler(r'^/edit/(?P<title>[A-Z][A-Za-z0-9]+)$', edit_handler)
    app.add_handler(r'^/assets/(?P<path>[\w\d\/-_.]+)$', assets_handler)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()
