import html
import json
from datetime import datetime
from difflib import context_diff

from os.path import exists

from utils import location
from web import Request


class Page:
    def __init__(self, request, title, content=None):
        self.title = title
        self.content = content
        self.request = request
        self.base = request.config.BASE_ROOT

    @classmethod
    def load(cls, request: Request, title: str):
        base = request.config.BASE_ROOT
        page_location = location(base, "pages/{title}.txt")

        try:
            with open(page_location, 'r+') as fileobj:
                page = cls(title)
                page.content = fileobj.read()
        except IOError:
            return None
        else:
            return page

    def save(self):
        page_location = location(self.base, f"pages/{self.title}.txt")
        log_location = location(self.base, f"pages/{self.title}.log")

        # Check a previous version of the content
        if exists(page_location):
            before = open(page_location, 'rb').read().decode()
        else:
            before = ''

        # If there is no change, don't do a thing.
        if before == self.content:
            return

        # Compare lines to later store the diff
        fromlines = before.splitlines(keepends=True)
        tolines = self.content.splitlines(keepends=True)

        diff = list(context_diff(fromlines, tolines))
        now = datetime.now().strftime("%Y/%m/%d %H:%M")
        log_entry = '{} - {}\n'.format(now, json.dumps(diff))

        with open(page_location, 'w+') as fileobj, open(log_location, 'a') as logobj:
            fileobj.write(self.content)
            logobj.write(log_entry)

    @property
    def history(self):
        log_location = location(self.base, f"pages/{self.title}.log")

        def parse_log():
            with open(log_location, 'r') as fobj:
                for line in fobj.readlines():
                    timestamp, data = line.split(' - ', maxsplit=1)

                    yield '<div class="entry clearfix">'
                    yield f'<div class="entry-timestamp">{timestamp}</div>'
                    yield '<div class="entry-diff">'

                    difflines = json.loads(data)
                    lines = difflines[3:]

                    for diffline in lines:
                        if diffline.startswith('- '):
                            yield '<div class="del">'
                        elif diffline.startswith('+ '):
                            yield '<div class="add">'
                        elif diffline.startswith('! '):
                            yield '<div class="mod">'
                        else:
                            yield '<div class="context">'

                        yield html.escape(diffline)

                        yield '</div>'

                    yield '</div>'
                    yield '</div>'

        return iter(parse_log())
