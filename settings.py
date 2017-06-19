import os


executable = 'agentd'
base_folder = '/var/run/socket_project_tmp'
db_folder_path = os.path.join(base_folder, 'db')
db_path = os.path.join(db_folder_path, 'store.db')

agent_settings = {
    'sock_address': os.path.join(base_folder, 'agent.sock'),
    'backlog_connection_number': 1,
}

worker_settings = {
    'sock_address_prefix': os.path.join(base_folder, 'worker.sock'),
    'backlog_connection_number': 1,
}
