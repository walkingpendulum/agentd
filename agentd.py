# coding: utf-8
import multiprocessing
import os
import signal
from urlparse import urlparse

import tornado.ioloop
import tornado.web
from tornado.escape import json_decode
from tornado.httpserver import HTTPServer
from tornado.netutil import bind_unix_socket
from tornado.web import HTTPError

import tasks
from daemonize import daemonize
from logger import create_logger, setup_tornado_loggers
from manager import ProcessManager
from settings import unix_socket_path, db_path, port
from utils import json_content, wrap_with_success_value, get_handler, post_handler


# noinspection PyAbstractClass
class AgentdBaseHandler(tornado.web.RequestHandler):
    """Базовый класс обработчика http запросов.

    Перенаправляет post/get запросы на одноименные не-приватные методы объекта.
    Если соответствующий метод не найден, бросает web.HTTPError(404).

    Идея и часть кода для диспатчинга post/get методов:
        http://code.activestate.com/recipes/576958-method-based-url-dispatcher-for-the-tornado-web-se/

    """
    def post(self):
        body = json_decode(self.request.body)
        return self._dispatch(body=body)

    def get(self):
        return self._dispatch()

    # noinspection PyDefaultArgument
    def _dispatch(self, body={}):
        parse_result = urlparse(self.request.uri)
        method = parse_result.path.lstrip('/')

        if method.startswith('_'):
            raise tornado.web.HTTPError(404)

        def not_found_raiser():
            raise HTTPError(404)

        callable_ = getattr(self, method, not_found_raiser)

        return callable_(**body)

    @staticmethod
    def _create_logger():
        raise NotImplementedError

    @staticmethod
    def _stop():
        """
        Потокобезопасно добавляем в следующую итерацию ioloop вызов функции spawn_killer
        (в свою очередь, spawn-killer отправляет SIGTERM в вызвавший его процесс).

        todo: если сервер запущен в несколько потоков, то убит будет только один

        :return:
        """
        ioloop = tornado.ioloop.IOLoop.instance()
        ioloop.add_callback(spawn_killer)   # trigger sighandler that triggers ioloop.stop()


# noinspection PyAbstractClass
class AgentdWebSocket(AgentdBaseHandler):
    """Обработка публичных методов API"""
    @get_handler
    @json_content
    @wrap_with_success_value
    def health(self):
        """
        GET

        Response example:
            {
                "success": 1,
                "response": "ok"
            }

        """
        return 'ok'

    # noinspection PyUnresolvedReferences
    @get_handler
    @json_content
    @wrap_with_success_value
    def info(self):
        """
        GET

        Response example:
            {
                "success": 1,
                "response": {
                    "running": [
                        {
                            "pid": 123,
                            "cmd": "worker",
                            "args": [999, "path/to/file"],
                            "kwargs": {
                                "key": "value"
                            }
                            "spawned_at": 1498761885.682778,
                            "host": "123.domain.server.com",
                        },
                        ...
                    ],
                    "waiting": [
                        ...
                    ]
                }
            }

        """
        return self.process_manager.info()

    # noinspection PyDefaultArgument, PyUnresolvedReferences
    @post_handler
    @json_content
    @wrap_with_success_value
    def run_task(self, cmd, args=tuple(), kwargs={}):
        """Запуск отдельного процесса с командой cmd, которая будет искаться в модуле tasks

        Поля args и kwargs будут использованы как аргументы при вызове команды: task(*args, **kwargs)

        POST

        Response example:
            {
                "success": 1,
            }

        :param cmd: str
        :param args: list
        :param kwargs: dict
        :return:
        """
        self.process_manager.spawn_process(cmd=cmd, args=args, kwargs=kwargs)

    @staticmethod
    def _create_logger():
        return create_logger('agentd_web_socket')

    # noinspection PyAttributeOutsideInit
    def initialize(self):
        self.logger = self._create_logger()
        self.process_manager = ProcessManager(db_path=db_path, tasks_module=tasks)


# noinspection PyAbstractClass
class AgentdUnixSocket(AgentdBaseHandler):
    """Обработка приватных методов API"""
    @get_handler
    @json_content
    @wrap_with_success_value
    def stop(self):
        self._stop()

    @post_handler
    @json_content
    @wrap_with_success_value
    def register_process(self, pid):
        self.process_manager.register_process(pid)

    @post_handler
    @json_content
    @wrap_with_success_value
    def unlink_process(self, pid):
        self.process_manager.unlink_process(pid)

    @post_handler
    @json_content
    @wrap_with_success_value
    def stop_registered_process(self, pid):
        self.process_manager.stop_registered_process(pid)

    @post_handler
    @json_content
    @wrap_with_success_value
    def kill_waiting_process(self, pid):
        self.process_manager.kill_waiting_process(pid)

    @staticmethod
    def _create_logger():
        return create_logger('agentd_unix_socket')

    # noinspection PyAttributeOutsideInit
    def initialize(self):
        self.logger = self._create_logger()
        self.process_manager = ProcessManager(db_path=db_path)


def spawn_killer():
    """Порождает отдельный процесс, который шлет SIGTERM в вызвавший его процесс."""
    def killer(pid):
        os.kill(pid, signal.SIGTERM)

    process_ = multiprocessing.Process(target=killer, args=(os.getpid(),))
    process_.start()


def make_websocket_app():
    return tornado.web.Application([
        (r"/.*", AgentdWebSocket),
    ])


def make_unixsocket_app():
    return tornado.web.Application([
        (r"/.*", AgentdUnixSocket),
    ])


def shutdown(web, unix):
    """Останавливаем оба сервера, удаляем unix сокет"""
    web.stop()

    unix.stop()
    os.unlink(unix_socket_path)


# noinspection PyUnusedLocal
def sighandler(*args, **kwargs):
    """Потокобезопасно добавляем ioloop.stop() в следующую итерацию ioloop"""
    ioloop = tornado.ioloop.IOLoop.instance()
    ioloop.add_callback_from_signal(ioloop.stop)


# noinspection PyProtectedMember,PyPep8
def main():
    """Старт демона, слушающего web и unix сокеты

    Запускаем два http сервера для обработки публичных и служебных запросов. Публичные запросы
    принимаются на web порт, служебные на внутренний unix socket.


    Начиная с версии 7.40 cURL умеет отправлять http запросы на unix сокеты с помощью флага
    --unix-socket. При таком сценарии использования все равно требуется указать какой-нибудь хост,
     всюду в коде для единообразия мы будем указывать localhost. Для отправки запроса из python требуются
     сторонние библиотеки, например requests-unixsocket. Примеры отправки запроса:

        $ curl --unix-socket /path/to/socket -X POST -d '{"message":"xyz"}' localhost/handler

        >>> import requests_unixsocket, requests
        >>> with requests_unixsocket.monkeypatch():
        ...     requests.post('http+unix://%s/handler' % unix_socket_path.replace('/', '%2F'), json={"message":"xyz"})



    Если выставлена переменная окружения DISABLE_DAEMON, то процесс запускается без демонизации.

    """
    if not os.getenv('DISABLE_DAEMON'):
        daemonize()

    setup_tornado_loggers()

    websocket_server = HTTPServer(make_websocket_app())
    websocket_server.bind(port)
    websocket_server.start()
    AgentdWebSocket._create_logger().info('Server started.')

    if not os.path.exists(os.path.dirname(unix_socket_path)):
        os.makedirs(os.path.dirname(unix_socket_path))
    unixsocket_server = HTTPServer(make_unixsocket_app())
    socket = bind_unix_socket(unix_socket_path)
    unixsocket_server.add_socket(socket)
    unixsocket_server.start()
    AgentdUnixSocket._create_logger().info('Server started.')

    # add ioloop.stop() as handler
    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)

    # start eventloop (serve both unix- and web- socket HTTP servers)
    tornado.ioloop.IOLoop.instance().start()

    # after the ioloop.stop() shut all servers down
    shutdown(web=websocket_server, unix=unixsocket_server)


if __name__ == '__main__':
    main()
