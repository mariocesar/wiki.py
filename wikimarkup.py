import contextlib
import html

import re
from io import StringIO


def wiki_text(value: str):
    """Renders text using a basic wiki syntax."""
    heading_pattern = re.compile(r'^(?P<level>[#]+)?\s*(?P<text>.*)')
    list_pattern = re.compile(r'^-\s+(?P<text>.+)')

    value = html.escape(value)

    # Redirects all print output to a buffer variable `output`
    with StringIO() as output, contextlib.redirect_stdout(output):

        inside_pre_block = False
        inside_list_block = False

        for chunk in value.split('\n'):
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

            if inside_list_block:
                if chunk.strip() == '':
                    # Close the list block if there is an empty line

                    inside_list_block = False
                    print('</ul>')

                    continue

            if chunk.startswith('#'):
                # Extracts level and text from the text

                match = heading_pattern.match(chunk)
                level = len(match.group('level'))
                text = match.group('text')

                print(f'<h{level}>{text}</h{level}>')

            elif chunk.startswith('```'):
                # Start preformatted block

                inside_pre_block = True
                print('<pre>')

            elif chunk.startswith('-'):
                # Start the list block if
                if not inside_list_block:
                    inside_list_block = True
                    print('<ul>')

                match = list_pattern.match(chunk)
                text = match.group('text')

                print(f'<li>{text}</li>')

            else:
                # Do not process empty paragraphs
                if not chunk.strip():
                    continue

                # Linkify. Search for the form [CamelCase] and
                # wraps a link on every ocurrence.
                chunk_with_links = re.sub(
                    r'\[([A-Z]\w+)\]',
                    r'<a href="/view/\1">\1</a> ',
                    chunk)

                # Paragraph
                print(f'<p>\n{chunk_with_links}\n</p>')

        # Check if there is still an open pre block, if it's close it
        if inside_pre_block:
            print('</pre>')

        return output.getvalue()
