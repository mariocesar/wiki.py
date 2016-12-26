import os
import string
from cgi import parse_header
from functools import wraps
from urllib.parse import unquote_plus, parse_qs
from wsgiref.handlers import format_date_time

import re

from utils import location, render_template


class Data:
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

    def __getitem__(self, item):
        """Get an item request.POST['item']"""
        return self.get(item)

    def __contains__(self, key):
        """True if field exists, 'field' in request.POST"""
        return key in self.data

    def get(self, key, default=None):
        if default and key not in self.data:
            return default

        try:
            value = self.data[key].pop()  # Just get the first value
        except KeyError:
            if default:
                return default
            raise

        return unquote_plus(value)


class Request:
    def __init__(self, environ):
        self.environ = environ
        self.path_info = environ.get('PATH_INFO', '/')
        self.method = environ['REQUEST_METHOD'].upper()
        self.content_type, self.content_params = parse_header(environ.get('CONTENT_TYPE', ''))

        self._POST = None
        self.META = environ
        self.META['PATH_INFO'] = self.path_info

        self.config = None
        self.resolver_match = None

    def POST(self):
        if not self._POST:
            self._POST = Data(self.environ)
        return self._POST


class Response:
    def __init__(self, content: bytes = None, status: int = None, headers: dict = None, content_type: str = None):
        if not content:
            self.content = b''
        self.content = content
        self.status_code = status
        self.content_type = content_type

        if not headers:
            self._headers = dict()
        else:
            self._headers = headers

    @property
    def headers(self):
        return [(str(k), str(v)) for k, v in self._headers.items()]

    def __iter__(self):
        if isinstance(self.content, bytes):
            return [self.content]
        elif isinstance(self.content, str):
            return [self.content.encode()]
        elif hasattr(self.content, '__iter'):
            return iter(self.content)

class Application:
    _handlers = []
    config = None

    def add_handler(self, urlpattern, handler):
        """Register a handler to later resolve by matching the url pattern."""
        urlpattern = re.compile(urlpattern)
        self._handlers.append((urlpattern, handler))

    def __call__(self, environ, start_response):
        for urlpattern, handler in self._handlers:
            match = urlpattern.match(environ.get('PATH_INFO', ''))
            request = Request(environ)
            request.resolver_match = urlpattern

            if match:
                return handler(request, start_response)

        return text_response('Not found', status=404)


# Utils

def wsgi_handler(func):
    @wraps(func)
    def inner(request, start_response):
        handler_kwargs = request.resolver_match.groupdict()
        response = func(request, **handler_kwargs)
        status = '%d OK' % response.status
        start_response(status, response.headers)
        return response

    return inner


@wsgi_handler
def redirect(request, location):
    """Shortcut to return a redirect response."""
    return Response(status=302, headers={'Location': location})


def template_response(request: Request, template_path: str, context: dict, status=None):
    """Shortcut to return an html response using a template."""
    template_path = location(request.config.BASE_ROOT, 'templates', template_path)
    content = render_template(template_path, **context)
    return Response(content, status=status, content_type='text/html; charset=utf-8')


def text_response(content: str, status=None):
    """Shortcut to return a text/plain response."""
    return Response(content, status=status, content_type='text/plain')


def fileobj_response(path: str):
    """Shortcut to return a text/plain response."""

    try:
        with open(path, 'rb') as fobj:
            fs = os.fstat(fobj.fileno())  # Get file size
            headers = {'Last-Modified': format_date_time(fs[8])}

            return Response(fobj, content_type='application/octect-stream', headers=headers, status=200)
    except OSError:
        return text_response('File not found', status=404)
