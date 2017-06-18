#!/usr/bin/env python
import os
import socket
import sys

from logger import create_logger
from settings import agent_settings

script_path = os.path.abspath('./%s' % __file__)

send_logger = create_logger('send')
receive_logger = create_logger('receive')


def send(message, logger=None):
    logger = logger or send_logger

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.connect(agent_settings['sock_address'])
    except socket.error as e:
        logger.error(e)
        return

    try:
        logger.info('sending "%s"' % message)
        sock.sendall(message)
    finally:
        sock.close()


def receive(sock, logger=None):
    logger = logger or receive_logger

    _message = []
    try:
        while True:
            data = sock.recv(16)
            if data:
                _message.append(data)
            else:
                break
        message = ''.join(_message)
    except Exception as e:
        logger.error(e)
        return
    finally:
        sock.close()

    return message


if __name__ == '__main__':
    msg = sys.argv[1]
    send(msg)
