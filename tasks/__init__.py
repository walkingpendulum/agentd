# coding=utf-8
import time

from commands.agentd_local_commands import unlink_at_exit, register_as_successfully_started
from tasks_workers import set_workers as set_workers_task
from tasks_workers import set_workers_globally as set_workers_globally_task
from tasks_workers import worker as worker_task


@unlink_at_exit
def sleep(num_sec):
    """Пример задачи для выполнения.

    Типичная задача перед началом полезной работы должна отправить подтверждение
    об успешном запуске с помощью вызова метода register_as_successfully_started,
    а также перед своим завершением отправить менежеру процессов запрос на удаление.
    Запрос на удаление можно слать вручную с помощью unlink_as_successfully_completed,
    а можно воспользоваться декоратором unlink_at_exit

    :param num_sec: int
    :return:
    """
    register_as_successfully_started()
    time.sleep(num_sec)

# ниже перечислены остальные задачи. такие странные присваивания сделаны для
# единообразия, а также чтобы зафиксировать публичное имя задачи, под которым
# она будет доступна для выполнения извне с помощью web обработчика в agentd

worker = worker_task
set_workers = set_workers_task
set_workers_globally = set_workers_globally_task
