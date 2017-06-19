#coding: utf-8
import os
import random
import signal
import string
import sys
import time

from agentd_commands import unlink_at_exit, register_as_successfully_started, stop_registered_process, info, send


@unlink_at_exit
def set_workers(num, path):
    register_as_successfully_started()

    num = int(num)
    if num < 0:
        return

    all_info = info()
    worker_info = {
        k: {
            pid: process_data for pid, process_data in v.items() if process_data['cmd'] == 'worker'
        } for k, v in all_info.items()
    }

    # todo: check if `waiting` worker becomes `running` and kill him
    workers_data = worker_info['running']
    if len(workers_data) > num:
        pids_to_kill = random.sample(workers_data, len(workers_data) - num)
        for pid in pids_to_kill:
            stop_registered_process(pid)
    elif len(workers_data) < num:
        # collect args for new worker processes
        # do some stuff
        not_free_names = {x['args'][0] for x in workers_data.values()}
        new_names = set()
        while True:
            name = ''.join(random.sample(string.ascii_lowercase, 16))
            if name not in not_free_names:
                not_free_names.add(name)
                new_names.add(name)

            if len(not_free_names) >= num:
                break

        cmd_with_args_list = ['worker %s %s' % (name, path) for name in new_names]

        # and send tasks to daemon
        for cmd in cmd_with_args_list:
            send(cmd)


@unlink_at_exit
def worker(name, path):
    register_as_successfully_started()

    def _terminate(signum, frame):
        os.unlink(file_path)
        sys.exit(0)
    signal.signal(signal.SIGTERM, _terminate)

    # do some stuff
    file_path = os.path.join(path, '%s.txt' % name)
    while True:
        with open(file_path, 'a') as f:
            f.write(''.join(random.sample(string.ascii_lowercase, 16)) + '\n')
        time.sleep(random.randint(3, 7))
