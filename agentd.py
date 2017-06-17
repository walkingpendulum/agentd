#!/usr/bin/env python
# coding: utf-8
import atexit
import logging
import multiprocessing
import os
import socket
import subprocess
import sys
from contextlib import contextmanager

import commands
from client import receive, script_path as client_script_path
from daemonize import daemonize
from exception import ServerStopException
from logger import create_logger
from settings import agent_settings

script_path = os.path.abspath('./%s' % __file__)

if __name__ == '__main__':
    daemonize()


@contextmanager
def stderr_redirect(logger_instance):
    class StreamToLogger(object):
        """
        Fake file-like stream object that redirects writes to a logger instance.
        see details at https://www.electricmonk.nl/log/2011/08/14/redirect-stdout-and-stderr-to-a-logger-in-python/
        """

        def __init__(self, logger, log_level=logging.INFO):
            self.logger = logger
            self.log_level = log_level
            self.linebuf = ''

        def write(self, buf):
            for line in buf.rstrip().splitlines():
                self.logger.log(self.log_level, line.rstrip())

        def flush(self):
            pass

    sl = StreamToLogger(logger_instance, logging.INFO)
    old_stderr = sys.stderr
    sys.stderr = sl

    try:
        yield
    finally:
        sys.stderr = old_stderr


class Agent(object):
    internal_cmd_set = {'stop', 'health', 'restart'}

    def __init__(self, sock_address, backlog_connection_number):
        self.sock_address = sock_address
        self.backlog_connection_number = backlog_connection_number

        self.logger = create_logger('server')
        self.processess_by_cmd = {}

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

    def stop(self):
        for process in self.processess_by_cmd.values():
            process.terminate()

        raise ServerStopException

    def health(self):
        self.logger.info('health check: ok')

    @staticmethod
    def restart():
        def _restart():
            subprocess.call('sudo %s' % script_path, shell=True)

        atexit.register(_restart())

    def spawn_process(self, cmd, callable, args_string):
        kwargs = {'target': callable}
        if args_string:
            kwargs.update({'args': (args_string, )})

        with stderr_redirect(self.logger):
            process = multiprocessing.Process(**kwargs)
            self.processess_by_cmd[cmd] = process
            process.start()

    def handle_connection_request(self, connection, client_address):
        message = receive(connection, logger=self.logger)
        if not message:
            return

        if message in self.internal_cmd_set:
            getattr(self, message)()
            return

        cmd, _, args_string = message.partition(' ')
        callable = getattr(commands, cmd, None)
        if callable is None:
            self.logger.error('Unknown command "%s"' % cmd)
            return

        self.spawn_process(cmd, callable, args_string or None)

    def run_server(self):
        sock = self.make_server_socket()

        while True:
            try:
                # Wait for a connection
                connection_params = sock.accept()

                self.handle_connection_request(*connection_params)
            except ServerStopException:
                self.logger.info('Got `exit` command, terminating...')
                break


if __name__ == '__main__':
    agent = Agent(**agent_settings)
    agent.run_server()
