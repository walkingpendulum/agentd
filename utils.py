import os
import random
import string
import subprocess
from distutils.spawn import find_executable

from settings import executable


def random_string(length=16):
    return ''.join([random.choice(string.ascii_lowercase) for _ in range(length)])


def get_source_folder():
    real_path = os.readlink(find_executable(executable))
    return os.path.dirname(real_path)


def start_application():
    subprocess.call('sudo %s start' % executable, shell=True)
