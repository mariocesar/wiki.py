import html
import os

from utils import location
from web import wsgi_handler, template_response, redirect, text_response, fileobj_response
from wikimarkup import wiki_text
from wikipage import Page


@wsgi_handler
def home_handler(request):
    """The main handler, just redirects to the default wiki Page."""
    return redirect('/view/Home')


@wsgi_handler
def view_handler(request, title):
    """View handler loads and render the given wiki Page."""

    page = Page.load(request, title)

    if not page:
        return redirect(f'/edit/{title}')

    title = html.escape(page.title)
    content = wiki_text(page.content)

    return template_response(request, 'view.html', {'title': title, 'content': content})


@wsgi_handler
def edit_handler(request, title):
    """Edit a wiki Page, if the page doesn't exists it will create it."""
    page = Page.load(request, title)

    if not page:
        page = Page(request, title)
        page.content = ''

    if request.method == 'POST':
        page.title = request.POST.get('title')
        page.content = request.POST.get('content', '')
        page.save()

        return redirect(f'/view/{title}')
    else:
        return template_response(request, 'edit.html', {
            'title': page.title,
            'content': page.content
        })


@wsgi_handler
def history_handler(request, title):
    """Shows change history for the page."""
    page = Page.load(request, title)

    if not page:
        return text_response('File not found', status=404)

    title = html.escape(page.title)

    return template_response(request, 'history.html', {
        'title': title,
        'history': '\n'.join(page.history)
    })


@wsgi_handler
def assets_handler(request, path):
    """Serves all found files in the assets directory."""
    path = location(request.config.BASE_ROOT, 'assets/', path)

    if os.path.isfile(path):
        return fileobj_response(path)

    return text_response('File Not found', status=404)
