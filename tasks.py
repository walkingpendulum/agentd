import time

from agentd_commands import register_as_successfully_started, unlink_at_exit


@unlink_at_exit
def sleep(args_string):
    register_as_successfully_started()
    time.sleep(int(args_string))


from tasks_workers import worker as worker_task
worker = worker_task

from tasks_workers import set_workers as set_workers_task
set_workers = set_workers_task

