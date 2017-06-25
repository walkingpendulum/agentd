import os


# base_folder = '/var/run/agentd'
# log_folder = '/var/log/agentd'
base_folder = os.path.abspath('./run')
log_folder = os.path.abspath('./log')


db_path = os.path.join(base_folder, 'db.json')
unix_socket_path = os.path.join(base_folder, 'agent.sock')
unix_socket_url_prefix = 'http+unix://%s' % unix_socket_path.replace('/', '%2F')
