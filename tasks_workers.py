# coding: utf-8
import os
import random
import signal
import string
import sys
import time

import requests
import requests_unixsocket

from agentd_commands import unlink_at_exit, register_as_successfully_started, stop_registered_process, info
from settings import unix_socket_url_prefix


@unlink_at_exit
def set_workers(num, path):
    register_as_successfully_started()

    num = int(num)
    if num < 0:
        return

    all_info = info()
    worker_info = {
        k: {
            process_data['pid']: process_data for process_data in v if process_data['cmd'] == 'worker'
        } for k, v in all_info.items()
    }

    # todo: check if `waiting` worker becomes `running` and kill him
    workers_data = worker_info['running']
    if len(workers_data) > num:
        pids_to_kill = random.sample(workers_data, len(workers_data) - num)
        for pid in pids_to_kill:
            stop_registered_process(pid)
    elif len(workers_data) < num:
        not_free_names = {x['kwargs']['name'] for x in workers_data.values()}
        new_names = set()
        while True:
            name = ''.join(random.sample(string.ascii_lowercase, 16))
            if name not in not_free_names:
                not_free_names.add(name)
                new_names.add(name)

            if len(not_free_names) >= num:
                break

        with requests_unixsocket.monkeypatch():
            for name in new_names:
                url = '%s/spawn_process' % unix_socket_url_prefix
                requests.post(url, json={'cmd': 'worker', 'kwargs': {'name': name, 'path': path}})


@unlink_at_exit
def worker(name, path):
    register_as_successfully_started()

    def _terminate(signum, frame):
        os.unlink(file_path)
        sys.exit(0)
    signal.signal(signal.SIGTERM, _terminate)

    file_path = os.path.join(path, '%s.txt' % name)
    while True:
        with open(file_path, 'a') as f:
            f.write(''.join(random.sample(string.ascii_lowercase, 16)) + '\n')
        time.sleep(random.randint(3, 7))
