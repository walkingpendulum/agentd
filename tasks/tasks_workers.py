# coding: utf-8
import os
import random
import signal
import string
import sys
import time
from bisect import bisect

from commands.agentd_local_commands import unlink_at_exit, register_as_successfully_started, stop_registered_process
from commands.agentd_remote_commands import info, cumulative_info, run_task
from settings import random_workers_path


@unlink_at_exit
def set_workers_globally(num):
    """Задача - глобальный оркестратор воркеров

    Пусть у нас имеется несколько серверов с запущенными на них локальными
    демонами agentd. Эта задача должна выполняться на одном из серверов, которому
    известны адреса всех остальных.

    После выполнения задачи гарантируется, что суммарное количество воркеров
    на всех известных хостах будет равным num.

    :param num: int
    :return:
    """
    register_as_successfully_started()

    # достаем данные обо всех процессах на всех хостах, оставляем только running
    all_info = cumulative_info()['running']

    # подсчитываем статистику

    host_to_workers_num = {host: len(processes_data) for host, processes_data in all_info.items()}
    workers_to_host_list = [[workers_num, h] for h, workers_num in host_to_workers_num.items()]
    total_workers_num = sum(w for w, h in workers_to_host_list)

    # round-robin стратегией подбираем такие цифры, чтобы количество воркеров
    # на всех машинах было равным num, а воркеры были размазаны по машинам
    # как можно равномернее
    #
    # если суммарное количество воркеров меньше необходимого, то воркеры будут
    # итеративно добавляться по одному, начиная с машин с наименьшим числом воркеров.
    # если воркеров было слишком много, то они будут итеративно убираться по одному,
    # начиная с машин с наибольшим количеством воркеров
    natural_order = total_workers_num > num
    handicap_value = -1 if total_workers_num > num else +1

    total_redundat_workers_num = total_workers_num - num
    while total_redundat_workers_num:
        workers_to_host_list.sort(reverse=not natural_order)
        record = [workers_num, host] = list(workers_to_host_list.pop())
        record[0] += handicap_value
        ind_to_insert = bisect(workers_to_host_list, record)
        workers_to_host_list.insert(ind_to_insert, record)
        total_redundat_workers_num += handicap_value

    # отправляем демонам на удаленных хостах задачи для локальной оркестрации
    # в соответствии с полученными выше цифрами
    for num, host in workers_to_host_list:
        run_task(cmd='set_workers', kwargs={'num': num}, url_prefix=host)


@unlink_at_exit
def set_workers(num, *args, **kwargs):
    """Задача - локальный оркестратор воркеров

    После запуска с параметром num гарантируется, что количество запущенных
    на этом хосте воркеров будет ровно num. Если воркеров было меньше, будут
    созданы новые, если больше, то лишние будут убиты (локальному демону
    agentd будет отправлен запрос stop_registered_process)

    :param num: количество воркеров
    :return:
    """
    register_as_successfully_started()

    if num < 0:
        return

    # достаем данные обо всех процессах на этом хосте
    all_info = info()

    # отфильтровываем только процессы с воркерами
    worker_info = {
        process_type: {
            process_data['pid']: process_data for process_data in processes_list if process_data['cmd'] == 'worker'
        } for process_type, processes_list in all_info.items()
    }

    # todo: check if `waiting` worker becomes `running` and kill him
    # оставляем только running
    workers_data = worker_info['running']

    if len(workers_data) > num:
        # процессов больше, чем нужно -- случайным образом выбираем жертв
        # и шлем демону запрос stop_registered_process
        pids_to_kill = random.sample(workers_data, len(workers_data) - num)
        for pid in pids_to_kill:
            stop_registered_process(pid)
    elif len(workers_data) < num:
        # процессов меньше, чем нужно -- создаем недостающих

        # здесь мы собираем необходимые нам данные для новых воркеров
        # some stuff here
        not_free_names = {x['kwargs']['name'] for x in workers_data.values()}
        new_names = set()
        while True:
            name = ''.join(random.sample(string.ascii_lowercase, 16))
            if name not in not_free_names:
                not_free_names.add(name)
                new_names.add(name)

            if len(not_free_names) >= num:
                break

        # и отправляем демону запрос на создание новых воркеров
        for name in new_names:
            run_task(cmd='worker', kwargs={'name': name})


@unlink_at_exit
def worker(name, path=random_workers_path):
    """Пример задачи-воркера

    Создает текстовый файл с именем name в папке path и через случайные
    промежутки времени пишет туда случайный текст.

    Важный прием - кастомный обработчик сигнала SIGTERM. При перехвате сигнала
    воркер осуществляет очистку данных и завершает работу. Это корректный by design
    способ завершения работы воркера.

    :param name: str
    :param path: str
    :return:
    """
    register_as_successfully_started()

    # noinspection PyUnusedLocal
    def _terminate(signum, frame):
        os.unlink(file_path)
        sys.exit(0)
    signal.signal(signal.SIGTERM, _terminate)

    file_path = os.path.join(path, '%s.txt' % name)
    while True:
        with open(file_path, 'a') as f:
            f.write(''.join(random.sample(string.ascii_lowercase, 16)) + '\n')
        time.sleep(random.randint(3, 7))
