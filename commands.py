import os
import time
from functools import wraps

from client import send


def _register_as_successfully_started():
    pid = str(os.getpid())
    msg = 'register %s' % pid
    send(msg)


def _unlink_as_successfully_completed():
    pid = str(os.getpid())
    msg = 'unlink %s' % pid
    send(msg)


def unlink_at_exit(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        res = func(*args, **kwargs)
        _unlink_as_successfully_completed()
        return res
    return wrapped


@unlink_at_exit
def sleep(args_string):
    _register_as_successfully_started()
    time.sleep(int(args_string))
