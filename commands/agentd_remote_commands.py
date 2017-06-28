import requests

from settings import local_host_prefix, hosts


def info(url_prefix=local_host_prefix):
    response = requests.get('%s/info' % url_prefix)
    return response.json()['response']


def cumulative_info():
    full_table = {'running': {}, 'waiting': {}}
    for host in hosts:
        url = '%s/info' % host
        response = requests.get(url)
        host_info = response.json()['response']
        for process_type, process_list in host_info.items():
            full_table[process_type][host] = process_list

    return full_table


def run_task(cmd, args=None, kwargs=None, url_prefix=local_host_prefix):
    return requests.post(
        '%s/run_task' % url_prefix,
        json={'cmd': cmd, 'kwargs': kwargs or {}, 'args': args or []}
    )

