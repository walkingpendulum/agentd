# coding=utf-8
import socket
import time


class Process(object):
    """Контейнер для данных о процессе"""

    dict_fields = (
        'pid',
        'cmd',
        'args',
        'kwargs',
        'spawned_at',
        'host',
    )

    # noinspection PyProtectedMember
    def __init__(self, cmd=None, process_obj=None, keep_unfilled=False):
        """
        Используется в двух сценариях: обертка над объектом multiprocessing.Process либо внутри
        метода from_record для создания пустого контейнера и дальнейшего заполнения данными из таблицы.
        В последнем случае нужно указать флаг keep_unfilled

        :param cmd: str
        :param keep_unfilled: bool
        :param process_obj: multiprocessing.Process object
        """
        assert (cmd is not None and process_obj is not None) or keep_unfilled
        self._waiting = True
        if keep_unfilled:
            return

        self.pid = process_obj.pid
        self.cmd = cmd
        self.args = process_obj._args
        self.kwargs = process_obj._kwargs
        self.host = socket.getfqdn()
        self.spawned_at = time.time()

    def set_as_running(self):
        self._waiting = False

    @classmethod
    def from_record(cls, waiting=False, **kwargs):
        obj = cls(keep_unfilled=True)
        for field in cls.dict_fields:
            setattr(obj, field, kwargs[field])

        if not waiting:
            obj.set_as_running()

        return obj

    @property
    def waisted_time_sec(self):
        if not self._waiting:
            return None

        now = time.time()
        return now - self.spawned_at

    def _asdict(self):
        return {k: getattr(self, k) for k in self.dict_fields}

    def __str__(self):
        return (
            'Process('
            'pid={self.pid}, '
            'cmd={self.cmd}, '
            'args={self.args}, '
            'kwargs={self.kwargs}, '
            '{time_field}'
            ')'
        ).format(
            self=self,
            time_field=(
                           'lifetime_sec=%s' if not self._waiting else 'waisted_time_sec=%s'
                       ) % int(time.time() - self.spawned_at)
        )
