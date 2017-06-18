import logging
import os


class StreamToLogger(object):
    """
    Fake file-like stream object that redirects writes to a logger instance.

    originally taken from
    https://www.electricmonk.nl/log/2011/08/14/redirect-stdout-and-stderr-to-a-logger-in-python/
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


def make_log_path(logger_name):
    folder = '/var/log/socket_project_tmp'
    if not os.path.exists(folder):
        os.makedirs(folder)

    return os.path.join(folder, '%s.log' % logger_name)


def set_root_handler(logger):
    root_handler = logging.FileHandler(make_log_path('all'))

    function_info_str = (
        '- [%(filename)s:%(lineno)s '
        '- %(funcName)s] '
    )

    fmt_str = (
        '%(asctime)s '
        '- %(name)s '
        '- %(levelname)s '
    ) + function_info_str + (
        '- %(message)s'
    )

    custom_formatter = logging.Formatter(fmt_str)
    root_handler.setFormatter(custom_formatter)
    root_handler.set_name('root')

    logger.addHandler(root_handler)


def create_logger(logger_name, level=logging.INFO):
    logger = logging.getLogger(logger_name)

    set_root_handler(logger)

    custom_handler = logging.FileHandler(make_log_path(logger_name))
    formatter = logging.Formatter(
        '%(asctime)s '
        '- %(levelname)s '
        '- [%(filename)s:%(lineno)s - %(funcName)s ] '
        '- %(message)s'
    )
    custom_handler.setFormatter(formatter)
    logger.addHandler(custom_handler)

    logger.setLevel(level)

    return logger
