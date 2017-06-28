import os
from functools import wraps

import requests
import requests_unixsocket

from settings import unix_socket_url_prefix


def unlink_as_successfully_completed():
    url = '%s/unlink_process' % unix_socket_url_prefix
    with requests_unixsocket.monkeypatch():
        requests.post(url, json={'pid': os.getpid()})


def unlink_at_exit(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        res = func(*args, **kwargs)
        unlink_as_successfully_completed()
        return res
    return wrapped


def register_as_successfully_started():
    url = '%s/register_process' % unix_socket_url_prefix
    with requests_unixsocket.monkeypatch():
        requests.post(url, json={'pid': os.getpid()})


def stop_registered_process(pid):
    url = '%s/stop_registered_process' % unix_socket_url_prefix
    with requests_unixsocket.monkeypatch():
        requests.post(url, json={'pid': pid})
