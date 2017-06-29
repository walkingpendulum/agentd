# agentd

#### Запуск:
```bash
$ python agentd.py --port 8888
```
Если опустить порт, то по умолчанию демон будет слушать 8888.
Адрес unix сокета настраивается в settings.py

Имеется докерфайл, для запуска демона в докере:
```bash
$ run --name agent1 -d -p 8001:8888 agentd-image
$ docker exec agent1 python agentd.py
```

#### Задачи
Задачи для запуска должны быть доступны при импорте модуля tasks, т.е. их нужно добавлять в `__init__.py`. Запросы на выполнение публично доступных задач должны отправляться на веб-сервер. Локальный сервер, слушающий uninx-сокет, используется для выполнения служебных задач и не подразумевался быть доступным извне.

* Начиная с версии 7.40 cURl умеет отправлять http запросы на unix сокеты с помощью флага
--unix-socket. При таком сценарии использования все равно требуется указать какой-нибудь хост,
 всюду в коде для единообразия мы будем указывать localhost. 
     ```bash
       $ curl --unix-socket /path/to/socket -X POST -d '{"message":"xyz"}' localhost/handler
    
    ```

* Для отправки запроса из python требуются
 сторонние библиотеки, например `requests` и `requests-unixsocket`
    ```python
    import requests_unixsocket, requests, os
    unix_socket_path = os.path.abspath('run/agent.sock')
    with requests_unixsocket.monkeypatch():
        requests.post('http+unix://%s/handler' % unix_socket_path.replace('/', '%2F'), json={"message":"xyz"})
    ```


#### Tutorial с использованием docker
Сборка образа:
```bash
$ docker build -t agentd-image .
```

Запуск двух контейнеров с локальными демонами на каждом:
```bash
$ docker run --name agent1 -d -p 8001:8888 agentd-image
$ docker run --name agent2 -d -p 8002:8888 agentd-image
$ docker exec agent1 python agentd.py
$ docker exec agent2 python agentd.py
```

Запуск локального демона, из которого будем запускать задачи:
```bash
$ python agentd.py
```

Проверка, что все работает:
```bash
$ curl http://localhost:8888/health
{
    "response": "ok",
    "success": 1
}

$ curl http://localhost:8001/health
{
    "response": "ok",
    "success": 1
}
$ curl http://localhost:8002/health
{
    "response": "ok",
    "success": 1
}
```

Отправляем запрос на задачу:
```bash
$ curl -X POST -d '{"cmd": "set_workers_globally", "kwargs": {"num": 3}}' http://localhost:8888/run_task
```
Теперь, если мы зайдем в контейнеры, то суммарно в них во всех будет три воркера, два на одном и один на другом. Если теперь выполнить аналогичную задачу и понизить количество воркеров до 1, то в одном из контейнеров воркеров не останется вовсе, а в другом их будет ровно один. Чтобы удалить всех воркеров, нужно выполнить `set_workers_globally` со значением `0`.

Также посмотреть количество процессов и данные о них можно командами:
```bash
$ curl http://localhost:8002/info
$ curl http://localhost:8001/info
$ curl http://localhost:8888/info
```