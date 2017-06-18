import gdbm
import logging
import multiprocessing
import os
import shelve
import signal
import sys
import traceback as tb

import commands
from exception import ServerStopException
from logger import create_logger, StreamToLogger
from settings import db_path, db_folder_path


class ProcessManager(object):
    def __init__(self):
        self.logger = create_logger('process_manager')

        try:
            if not os.path.exists(db_folder_path):
                os.makedirs(db_folder_path)
            self.storage = shelve.open(db_path, writeback=True)
        except gdbm.error as e:
            if e.args == (35, 'Resource temporarily unavailable'):
                raise ServerStopException
            else:
                self.logger.error(tb.format_exc())
                raise
        except Exception:
            self.logger.error(tb.format_exc())
            raise

        self.running_processes_registry = self.storage.setdefault('running', {})
        self.waiting_for_registration_processes_registry = self.storage.setdefault('waiting', {})

    def info(self):
        info = {
            'running': self.running_processes_registry,
            'waiting': self.waiting_for_registration_processes_registry
        }
        return info

    def stop(self, keep_processess=False):
        if not keep_processess:
            self.stop_all_processes()

        self.storage.close()

    def stop_all_processes(self):
        for pid in self.running_processes_registry:
            self.stop_process(pid)
        self.storage['running'] = {}

        for pid in self.waiting_for_registration_processes_registry:
            self.stop_process(pid)
            self.storage['waiting'] = {}

    def stop_process(self, pid):
        try:
            os.kill(int(pid), signal.SIGTERM)
        except OSError:
            pass

    def register_process(self, pid):
        try:
            process_data = self.waiting_for_registration_processes_registry[pid]
            del self.storage['waiting'][pid]
        except KeyError:
            self.logger.error('Attempt to register process with pid %s failed' % pid)
            return
        else:
            if pid in self.running_processes_registry:
                self.logger.error('Attempt to register already presented process with pid %s, aborting' % pid)
                return

            self.running_processes_registry[pid] = process_data
            self.logger.info(
                'Successfully register process with pid: {pid}, cmd: {cmd} args: {args}'.format(
                    pid=pid, **process_data
                )
            )

    def unlink(self, pid):
        self.stop_process(pid)
        process_data = self.storage['running'][pid]
        del self.storage['running'][pid]
        self.logger.info(
            'Sucessfully unlink process with pid: {pid}, cmd: {cmd}, args: {args}'.format(
                pid=pid, **process_data
            )
        )

    def spawn_process(self, cmd, args_string):
        callable = getattr(commands, cmd, None)
        if callable is None:
            self.logger.error('Unknown command "%s"' % cmd)
            return

        process_kwargs = {'target': callable}
        cmd_args = []
        if args_string:
            cmd_args.append(args_string)
        process_kwargs.update({'args': tuple(cmd_args)})

        old_err = sys.stderr
        sys.stderr = StreamToLogger(self.logger, log_level=logging.ERROR)
        process = multiprocessing.Process(**process_kwargs)

        try:
            process.start()
        except Exception:
            msg = tb.format_exc()
            self.logger.error(msg)
        else:
            process_data = {'cmd': cmd, 'args': cmd_args}
            pid = str(process.pid)
            self.waiting_for_registration_processes_registry[pid] = process_data
        finally:
            sys.stderr = old_err
