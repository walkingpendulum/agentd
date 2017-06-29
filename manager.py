# coding: utf-8
import logging
import multiprocessing
import os
import signal
import sys
import traceback as tb

from tinydb import TinyDB, Query

from logger import create_logger, StreamToLogger
from models import Process as ProcessModel

q = Query()


# noinspection PyProtectedMember
class ProcessManager(object):
    """Менеджер запущенных процессов

    При каждом запросе к демону agentd создается экземпляр ProcessManager и открывается
    соединение с базой данных. После завершения обработки соединение с БД закрывается
    и экземпляр менеджера уничтожается.


    Все запущенные в рамках исполнения заданий процессы делятся на running и waiting.

    Когда процесс только запущен, он считается waiting и записывается в таблицу
    _waiting_for_registration_processes_table. Это необходимо для отслеживания статуса
    процесса и мониторинга его успешного запуска.

    Для того чтобы перевести процесс в running, нужно послать запрос на /register_process
    (метод commands.agentd_local_commands.register_as_successfully_started). После этого
    подтверждания от процесса менджер переведет его в running и запишет в таблицу
    _running_processes_table.

    С помощью демона agentd запросы проксируются в этот менджер, который по стуи является бекендом
    этого фреймворка. Менеджер и выполняет реальное обслуживание запросов. Задачи для выполнения бывают
    либо служебными (например, регистрация/разрегистрация процессов, остановка процессов и т.д.),
    либо задачами из модуля tasks.


    В качестве базы данных используется TinyDB.

    XXX: использовать tinyrecord (примеры здесь https://github.com/eugene-eeo/tinyrecord) для атомарных операций
    """
    def __init__(self, db_path, tasks_module=None):
        self.logger = create_logger('process_manager')
        self.db = TinyDB(db_path)
        self.tasks = tasks_module
        self._waiting_for_registration_processes_table = self.db.table('waiting')
        self._running_processes_table = self.db.table('running')

    @property
    def running(self):
        return self._running_processes_table

    @property
    def waiting(self):
        return self._waiting_for_registration_processes_table

    def info(self):
        info = {
            'running': [ProcessModel.from_record(**rec)._asdict() for rec in self.running],
            'waiting': [ProcessModel.from_record(waiting=True, **rec)._asdict() for rec in self.waiting],
        }

        return info

    def stop(self, keep_processess=False):
        """Завершение работы менеджера, сохранение данных, завершение процессов (если требуется)

        :param keep_processess: нужно ли останавливать запущенные процессы
        :return:
        """
        if not keep_processess:
            self.stop_all_processes()

        self.db.close()

    def stop_all_processes(self):
        running = self.running.all()   # prevent the `changed size during iteration` error
        for record in running:
            self.stop_registered_process(pid=record['pid'])

        for record in self.waiting:
            self._kill_process(pid=record['pid'])
        self.waiting.purge()

    def stop_registered_process(self, pid):
        """Остановка процесса, удаление его из списка работающих

        :param pid:
        :return:
        """
        self._kill_process(pid)
        self.unlink_process(pid)

    def _kill_process(self, pid):
        """Завершение процесса

        :param pid:
        :return:
        """
        try:
            os.kill(int(pid), signal.SIGTERM)
        except OSError:
            pass
        else:
            self.logger.info('Kill process with pid %s' % pid)

    def register_process(self, pid):
        """Перенос процесса из списка запущенных в список работающих (штатно запустился и начал работу)

        :param pid:
        :return:
        """
        process = ProcessModel.from_record(waiting=True, **self.waiting.get(q.pid == pid))
        self.waiting.remove(q.pid == pid)

        if self.running.contains(q.pid == process.pid):
            self.logger.error('Attempt to register already presented process with pid %s, aborting' % process.pid)
            return

        self.running.insert(process._asdict())
        self.logger.info('Register %s' % process)

    def unlink_process(self, pid):
        """Удаление процесса из списка работающих (когда он завершился)

        :param pid:
        :return:
        """
        process = ProcessModel.from_record(**self.running.get(q.pid == pid))
        self.running.remove(q.pid == pid)
        self.logger.info('Unlink %s' % process)

    def kill_waiting_process(self, pid):
        """Остановка процесса (если он есть) и удаление его из списка ждущих подтвержения (если он там есть)

        :param pid:
        :return:
        """
        self._kill_process(pid)
        self.waiting.remove(q.pid == pid)

    def spawn_process(self, cmd, args, kwargs):
        """Порождает новый процесс с задачей. Задача берется из модуля tasks

        stderr поток при запуске процесса перенаправляется в логгер.
        XXX: перенаправление искажает реальный traceback

        :param kwargs:
        :param cmd:
        :param args:
        :return:
        """
        callable_ = getattr(self.tasks, cmd, None)
        if callable_ is None:
            self.logger.error('Unknown command "%s"' % cmd)
            return

        old_err = sys.stderr
        sys.stderr = StreamToLogger(self.logger, log_level=logging.ERROR)

        # noinspection PyBroadException
        try:
            process_ = multiprocessing.Process(target=callable_, args=args, kwargs=kwargs)
            process_.start()
        except Exception:
            msg = tb.format_exc()
            self.logger.error(msg)
        else:
            process = ProcessModel(cmd=cmd, process_obj=process_)
            self.waiting.insert(process._asdict())
            self.logger.info('Spawn %s' % process)
        finally:
            sys.stderr = old_err
