import os
from tornado.options import define, parse_command_line, options

define("port", default="8888")
parse_command_line()

base_folder = os.path.abspath('./run')
log_folder = os.path.abspath('./log')

db_path = os.path.join(base_folder, 'db.json')
unix_socket_path = os.path.join(base_folder, 'agent.sock')
unix_socket_url_prefix = 'http+unix://%s' % unix_socket_path.replace('/', '%2F')

port = options.port
local_host_prefix = 'http://localhost:%s' % port

hosts = [
    'http://localhost:8001',
    'http://localhost:8002'
]

random_workers_path = os.path.join(os.path.dirname(__file__), 'random_workers')
