import json
import random
import string
from functools import wraps

from tornado.web import HTTPError


def random_string(length=16):
    return ''.join([random.choice(string.ascii_lowercase) for _ in range(length)])


def json_content(func):
    @wraps(func)
    def wrapped(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        self.add_header('Content-Type', 'application/json')

        self.write(json.dumps(result, indent=4, ensure_ascii=False))
        self.write('\n')
    return wrapped


def wrap_with_success_value(func):
    @wraps(func)
    def wrapped(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        success = {'success': 1}

        if result is None:
            return success
        else:
            return {'success': 1, 'response': result}

    return wrapped


def get_handler(func):
    @wraps(func)
    def wrapped(self, *args, **kwargs):
        if not self.request.method == 'GET':
            raise HTTPError(404)

        return func(self, *args, **kwargs)
    return wrapped


def post_handler(func):
    @wraps(func)
    def wrapped(self, *args, **kwargs):
        if not self.request.method == 'POST':
            raise HTTPError(404)

        return func(self, *args, **kwargs)

    return wrapped
