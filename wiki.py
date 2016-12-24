import io
import os
import re
from contextlib import contextmanager, redirect_stdout
from string import Template
from urllib.parse import parse_qs, quote_plus, unquote_plus
from wsgiref.simple_server import make_server


# Classes

class Page:
    title = None
    content = None

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
    start_response("302 OK", [('Location', location), ])

    return [b'']


def render_template(template_path, **context):
    """Render a string using a file as template and the given context."""
    with open(template_path, 'r') as fileobj:
        tpl = Template(fileobj.read())

    return tpl.safe_substitute(**context).encode('utf-8')


def template_response(start_response, template_path, context, status=200):
    """Shortcut to return a text/html response using a template."""
    start_response(f"{status} OK", [('Content-Type', 'text/html; charset=utf-8')])
    content = render_template(template_path, **context)

    return [content]


def text_response(start_response, content, status=200):
    """Shortcut to return a text/plain response."""
    start_response(f"{status} OK", [('Content-Type', 'text/plain; charset=utf-8')])

    return [content.encode()]


def escape(value):
    """Replace special characters to return a safe sequence."""
    return (value
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', "&quot;"))


def wiki_text(value):
    """Escape and renders text using a basic wiki syntax"""

    value = escape(value)

    # Redirects all print output to a buffer variable `output`
    with io.StringIO() as output, redirect_stdout(output):

        for chunk in value.split('\n'):
            chunk = chunk.strip()

            if chunk.startswith('#'):
                # Extracts level and text from the text
                match = re.match('^(?P<level>[#]+)?\s*(?P<text>.*)', chunk)
                level = len(match.group('level'))
                text = match.group('text')

                print(f'<h{level}>{text}</h{level}>')
            else:

                # linkify
                chunk_with_links = re.sub(
                    r'\[([A-Z]\w+)\]',
                    r'<a href="/view/\1">\1</a> ',
                    chunk)

                # paragraph
                print(f'<p>{chunk_with_links}</p>')

        return output.getvalue()


# Handlers

def home_handler(environ, start_response):
    return redirect(start_response, '/view/Home')


def view_handler(environ, start_response):
    title = environ['app.match'].group('title')

    page = Page.load(title)

    if not page:
        return redirect(start_response, f'/edit/{title}')

    context = {'title': escape(page.title),
               'content': wiki_text(page.content)}

    return template_response(start_response, 'templates/view.html', context)


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

        return template_response(
            start_response, 'templates/edit.html',
            {'title': page.title, 'content': page.content})


# WSGI Application

class Application:
    _handlers = []

    def add_handler(self, path, handler):
        path_pattern = re.compile(path)
        self._handlers.append((path_pattern, handler))

    def __call__(self, environ, start_response):
        for path_pattern, handler in self._handlers:
            match = path_pattern.match(environ.get('PATH_INFO', ''))
            if match:
                environ['app.match'] = match
                return handler(environ, start_response)

        return text_response(start_response, 'Not found', status=404)


with make_server('', 8000, Application()) as httpd:
    print("Serving on port 8000...")

    httpd.application.add_handler(r'^/$', home_handler)
    httpd.application.add_handler(r'^/view/(?P<title>\w+)$', view_handler)
    httpd.application.add_handler(r'^/edit/(?P<title>\w+)$', edit_handler)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()
