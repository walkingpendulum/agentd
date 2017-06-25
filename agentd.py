# coding: utf-8
import logging
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

from daemonize import daemonize
from logger import create_logger, set_root_handler
from manager import ProcessManager
from settings import unix_socket_path, db_path
from utils import json_content, wrap_with_success_value, get_handler, post_handler


# noinspection PyAbstractClass
class Agentd(tornado.web.RequestHandler):
    @get_handler
    @json_content
    @wrap_with_success_value
    def health(self):
        return 'ok'

    @get_handler
    @json_content
    @wrap_with_success_value
    def info(self):
        return self.process_manager.info()

    @get_handler
    @json_content
    @wrap_with_success_value
    def stop(self):
        self._stop()

    # @get_handler
    # @json_content
    # @wrap_with_success_value
    # def restart(self):
    #     self._set_restart_flag()
    #     self._stop()

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
    def echo(self, msg):
        return "Echo: %s" % msg

    @post_handler
    @json_content
    @wrap_with_success_value
    def kill_waiting_process(self, pid):
        self.process_manager.kill_waiting_process(pid)

    # noinspection PyDefaultArgument
    @post_handler
    @json_content
    @wrap_with_success_value
    def spawn_process(self, cmd, args=tuple(), kwargs={}):
        self.process_manager.spawn_process(cmd=cmd, args=args, kwargs=kwargs)

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

    # noinspection PyAttributeOutsideInit
    def initialize(self):
        self.logger = create_logger('server')
        self.process_manager = ProcessManager(db_path=db_path)

    @staticmethod
    def _stop():
        ioloop = tornado.ioloop.IOLoop.instance()
        ioloop.add_callback(spawn_killer)

    # @staticmethod
    # def _set_restart_flag():
    #     db = TinyDB(db_path)
    #     signals_table = db.table('signals')
    #     signals_table.insert({'signal': 'restart'})
    #     db.close()
    #
    # @staticmethod
    # def _pop_restart_flag():
    #     db = TinyDB(db_path)
    #     signals_table = db.table('signals')
    #     restart_flag = signals_table.contains(Query().signal == 'restart')
    #     signals_table.remove(Query().signal == 'restart')
    #     db.close()
    #     return restart_flag


def spawn_killer():
    def killer(pid):
        os.kill(pid, signal.SIGTERM)

    process_ = multiprocessing.Process(target=killer, args=(os.getpid(),))
    process_.start()


def make_app():
    app = tornado.web.Application([
        (r"/.*", Agentd),
    ])
    return app


def setup_tornado_loggers():
    access_log = logging.getLogger("tornado.access")
    app_log = logging.getLogger("tornado.application")
    gen_log = logging.getLogger("tornado.general")

    access_log.setLevel(logging.INFO)
    app_log.setLevel(logging.INFO)
    gen_log.setLevel(logging.INFO)

    set_root_handler(access_log)
    set_root_handler(app_log)
    set_root_handler(gen_log)


def shutdown(server, cwd):
    server.stop()
    os.unlink(unix_socket_path)

    process_manager = ProcessManager(db_path=db_path)
    process_manager.stop()

    # restart_flag = Agentd._pop_restart_flag()
    # process_manager.stop(keep_processess=restart_flag)

    # if restart_flag:
    #     os.chdir(cwd)
    #     atexit.register(lambda: subprocess.call('%s %s' % (sys.executable, ' '.join(sys.argv)), shell=True))


def sighandler(*args, **kwargs):
    ioloop = tornado.ioloop.IOLoop.instance()
    ioloop.add_callback_from_signal(ioloop.stop)


def run_server():
    current_path = os.getcwd()
    if not os.getenv('DISABLE_DAEMON'):
        daemonize()

    setup_tornado_loggers()

    app = make_app()
    server = HTTPServer(app)

    if not os.path.exists(os.path.dirname(unix_socket_path)):
        os.makedirs(os.path.dirname(unix_socket_path))
    socket = bind_unix_socket(unix_socket_path)
    server.add_socket(socket)   # curl --unix-socket /path/to/socket -X POST -d '{"message":"xyz"}' localhost/handler
    server.bind(8888)   # curl -X POST -d '{"message":"xyz"}' localhost:8888/handler

    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)

    server.start()
    create_logger('server').info('Server started.')

    tornado.ioloop.IOLoop.instance().start()
    shutdown(server=server, cwd=current_path)


if __name__ == '__main__':
    run_server()
