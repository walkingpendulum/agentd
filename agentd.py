#!/usr/bin/env python
# coding: utf-8
import atexit
import json
import os
import shlex
import subprocess
import sys
import time
import traceback as tb

from daemonize import daemonize
from exception import ServerStopException
from logger import create_logger
from manager import ProcessManager
from network import receive, send, make_server_socket
from settings import agent_settings
from utils import get_source_folder, start_application


class Agent(object):
    internal_cmd_set = {
        'health',
        'version',
        'stop',
        'restart',
        'info',
        'echo',
        'register_process',
        'unlink_process',
        'stop_registered_process',
        'kill_waiting_process',
    }

    def __init__(self, sock_address, backlog_connection_number):
        self.logger = create_logger('server')

        self.sock_address = sock_address
        self.backlog_connection_number = backlog_connection_number

        try:
            self.process_manager = ProcessManager()
        except ServerStopException:
            self.logger.error('running agentd process detected, aborting')
            sys.exit(1)
        except Exception:
            self.logger.error('Can\'t instantiate ProcessManager, aborting')
            sys.exit(1)

    def health(self, return_address=None):
        msg = 'health check: ok'

        if not return_address:
            self.logger.info(msg)
        else:
            send(msg, sock_address=return_address)

    def version(self, return_address=None):
        source_folder = get_source_folder()
        version = subprocess.check_output('git -C "%s" status' % source_folder, shell=True).decode()

        msg = version

        if not return_address:
            self.logger.info(msg)
        else:
            send(msg, sock_address=return_address)

    def info(self, return_address=None):
        info_dict = self.process_manager.info()

        waiting_dict = info_dict['waiting']
        now = time.time()
        for pid, data in waiting_dict.items():
            data['waisted_time_sec'] = now - data['spawned_at']

        msg = json.dumps(info_dict, indent=4)

        if not return_address:
            self.logger.info(msg)
        else:
            send(msg, sock_address=return_address)

    def stop(self, restart=False):
        self.process_manager.stop(keep_processess=restart)
        raise ServerStopException

    def restart(self):
        atexit.register(start_application())
        self.stop(restart=True)

    def register_process(self, pid):
        self.process_manager.register_process(pid)

    def unlink_process(self, pid):
        self.process_manager.unlink_process(pid)

    def stop_registered_process(self, pid):
        self.process_manager.stop_registered_process(pid)

    def echo(self, msg):
        self.logger.info("Echo: %s" % msg)

    def kill_waiting_process(self, pid):
        self.process_manager.kill_waiting_process(pid)

    def handle_connection_request(self, sock):
        message = receive(sock, logger=self.logger)
        if not message:
            return

        cmd, _, args_string = message.partition(' ')
        args = shlex.split(args_string)
        if cmd in self.internal_cmd_set:
            getattr(self, cmd)(*args)
            return

        self.process_manager.spawn_process(cmd, args)

    def run_server(self):
        server_sock = make_server_socket(**agent_settings)

        self.logger.info('agentd started')
        while True:
            try:
                # Wait for a connection
                sock, client_address = server_sock.accept()

                self.handle_connection_request(sock)
            except ServerStopException:
                self.logger.info('Got `exit` command, terminating...')
                sys.exit(0)
            except Exception:
                self.logger.error(tb.format_exc())
                continue


if __name__ == '__main__':
    msg = ' '.join(sys.argv[1:])

    if msg == 'start':
        if not os.getenv('DISABLE_DAEMON'):
            daemonize()

        agent = Agent(**agent_settings)
        agent.run_server()
    else:
        send(msg)
