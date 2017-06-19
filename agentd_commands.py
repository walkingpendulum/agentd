import json
import os
from functools import wraps

from network import send_and_receive_answer, send


def register_as_successfully_started():
    pid = str(os.getpid())
    msg = 'register_process %s' % pid
    send(msg)


def unlink_as_successfully_completed():
    pid = str(os.getpid())
    msg = 'unlink_process %s' % pid
    send(msg)


def unlink_at_exit(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        res = func(*args, **kwargs)
        unlink_as_successfully_completed()
        return res
    return wrapped


def info():
    _msg = send_and_receive_answer('info')
    msg = json.loads(_msg)

    return msg


def stop_registered_process(pid):
    msg = 'stop_registered_process %s' % pid
    send(msg)
