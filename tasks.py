import time

from agentd_commands import register_as_successfully_started, unlink_at_exit


@unlink_at_exit
def sleep(args_string):
    register_as_successfully_started()
    time.sleep(int(args_string))
