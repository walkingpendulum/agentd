#!/usr/bin/env python
import os
import socket
import traceback as tb

from logger import create_logger
from settings import agent_settings, base_folder
from utils import random_string

send_logger = create_logger('send')
receive_logger = create_logger('receive')
stderr_logger = create_logger('stderr')


def make_server_socket(sock_address, backlog_connection_number):
    # Make sure the socket does not already exist
    try:
        os.unlink(sock_address)
    except OSError:
        if os.path.exists(sock_address):
            raise

    # Create a UDS socket
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    # Bind the socket to the port
    sock.bind(sock_address)

    # Listen for incoming connections
    sock.listen(backlog_connection_number)

    return sock


def send(message, sock_address=None, logger=None):
    logger = logger or send_logger

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock_address = sock_address or agent_settings['sock_address']
    try:
        sock.connect(sock_address)
    except socket.error as e:
        logger.error(e)
        return

    try:
        sock.sendall(message)
    finally:
        sock.close()


def receive(sock, buffer=4096, logger=None):
    logger = logger or receive_logger

    _message = []
    try:
        while True:
            data = sock.recv(buffer)
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


def send_and_receive_answer(msg_to_send):
    tmp_server_sock_address = os.path.join(base_folder, 'tmp_%s.sock' % random_string())
    try:

        server_sock = make_server_socket(tmp_server_sock_address, 1)

        send('%s %s' % (msg_to_send, tmp_server_sock_address))

        sock, _ = server_sock.accept()
        answer = receive(sock)

        return answer

    except Exception:
        stderr_logger.error(tb.format_exc())

    finally:
        try:
            os.unlink(tmp_server_sock_address)
        except OSError:
            if os.path.exists(tmp_server_sock_address):
                raise

