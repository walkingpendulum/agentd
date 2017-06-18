import time
import os
from client import send


def _register_as_successfully_started():
    pid = str(os.getpid())
    msg = 'register %s' % pid
    send(msg)


def sleep(args_string):
    _register_as_successfully_started()
    time.sleep(int(args_string))
