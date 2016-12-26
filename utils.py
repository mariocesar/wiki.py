import string
from os.path import normcase, join, abspath


def location(base, *paths):
    """
    Joins one or more path components to the base path component.
    Returns a normalized, absolute version of the final path.
    Check the resulting path is located inside the base path, raise ValueError if not.
    """
    paths = [normcase(p) for p in paths]
    path = abspath(join(base, *paths))

    # Check if the resulting path is part of the base part
    if not path.startswith(base):
        raise ValueError('Resulting path is not inside the base path.')

    return path


def render_template(template_path: str, **context):
    """Render a string using a file as template and the given context."""

    with open(template_path, 'r') as fileobj:
        tpl = string.Template(fileobj.read())

    return tpl.safe_substitute(**context)
