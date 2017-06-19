#!/usr/bin/env python
# coding: utf-8
import atexit
import json
import os
import socket
import subprocess
import sys
import traceback as tb

from client import receive
from daemonize import daemonize
from exception import ServerStopException
from logger import create_logger
from manager import ProcessManager
from settings import agent_settings

script_path = os.path.abspath('./%s' % __file__)


if __name__ == '__main__' and not os.getenv('DISABLE_DAEMON'):
    daemonize()


class Agent(object):
    internal_cmd_set = {'stop', 'health', 'restart', 'register', 'unlink', 'info'}

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

    def make_server_socket(self):
        # Make sure the socket does not already exist
        try:
            os.unlink(self.sock_address)
        except OSError:
            if os.path.exists(self.sock_address):
                raise

        # Create a UDS socket
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        # Bind the socket to the port
        sock.bind(self.sock_address)

        # Listen for incoming connections
        sock.listen(self.backlog_connection_number)

        return sock

    def stop(self, restart=False):
        self.process_manager.stop(keep_processess=restart)
        raise ServerStopException

    def health(self):
        self.logger.info('health check: ok')

    def restart(self):
        def _restart():
            subprocess.call('sudo %s' % script_path, shell=True)

        atexit.register(_restart())
        self.stop(restart=True)

    def register(self, pid):
        self.process_manager.register_process(pid)

    def unlink(self, pid):
        self.process_manager.unlink(pid)

    def info(self):
        info_dict = self.process_manager.info()
        self.logger.info(json.dumps(info_dict, indent=4))

    def handle_connection_request(self, connection, client_address):
        message = receive(connection, logger=self.logger)
        if not message:
            return

        cmd, _, args_string = message.partition(' ')
        if cmd in self.internal_cmd_set:
            getattr(self, cmd)(*(args_string.split(' ') if args_string else []))
            return

        self.process_manager.spawn_process(cmd, args_string or None)

    def run_server(self):
        sock = self.make_server_socket()

        self.logger.info('agent started')
        while True:
            try:
                # Wait for a connection
                connection_params = sock.accept()

                self.handle_connection_request(*connection_params)
            except ServerStopException:
                self.logger.info('Got `exit` command, terminating...')
                break


if __name__ == '__main__':
    logger = create_logger('stderr')

    try:
        agent = Agent(**agent_settings)
        agent.run_server()
    except Exception:
        logger.error(tb.format_exc())
