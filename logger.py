import logging
import os


def make_log_path(logger_name):
    folder = '/var/log/socket_project_tmp'
    if not os.path.exists(folder):
        os.makedirs(folder)

    return os.path.join(folder, '%s.log' % logger_name)


def create_logger(logger_name):
    logger = logging.getLogger(logger_name)

    fh = logging.FileHandler(make_log_path(logger_name))
    logger.addHandler(fh)

    logger.setLevel(logging.INFO)

    return logger
