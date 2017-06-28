import time

from commands.agentd_local_commands import unlink_at_exit, register_as_successfully_started
from tasks_workers import set_workers as set_workers_task
from tasks_workers import set_workers_globally as set_workers_globally_task
from tasks_workers import worker as worker_task


@unlink_at_exit
def sleep(args_string):
    register_as_successfully_started()
    time.sleep(int(args_string))


worker = worker_task
set_workers = set_workers_task
set_workers_globally = set_workers_globally_task
