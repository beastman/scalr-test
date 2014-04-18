#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import re
import paramiko
import json


def rel(*x):
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), *x)


def format_data(data):
    """Форматирует полученные данные о хосте"""
    result = ''
    result += 'Load Averages: {0}\n'.format(' '.join(str(x) for x in data['load_average']))
    result += 'Block Devices:\n'
    for row in data['block_device_names']:
        result += row + '\n'
    result += 'CPU Cores: {0}\n'.format(data['cpu_cores'])
    result += 'Mount Points:\n'
    for row in data['mount_points'].keys():
        result += '{0} -> {1}\n'.format(row, data['mount_points'][row])
    result += 'Root FS Space Available: {0}\n'.format(data['rootfs_free_space'])
    result += 'Installed Packages:\n'
    result += ','.join(data['installed_packages'])
    return result

CONNECTION_STRING_RE = re.compile('^(?P<username>.+?):(?P<password>.+?)@(?P<host>.+):(?P<port>\d+)$')
HOST_INFO_SCRIPT_PATH = rel('host_info.py')
REMOTE_SERVER_BASE_PATH = '/tmp/'
REMOTE_SERVER_PYTHON_PATH = '/usr/bin/python'

if __name__ == "__main__":
    if not os.path.exists(HOST_INFO_SCRIPT_PATH):
        raise Exception('Host info script does not exist.')
    if len(sys.argv) < 2:
        raise Exception('Connection string is missing')
    if not CONNECTION_STRING_RE.match(sys.argv[1]):
        raise Exception('Connection string should be in following format: user:pass@host:port')
    #Коннектимся
    connection_data = CONNECTION_STRING_RE.match(sys.argv[1]).groupdict()
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=connection_data['host'],
        username=connection_data['username'],
        password=connection_data['password'],
        port=int(connection_data['port']),
        timeout=10
    )
    #Заливаем
    transport = client.get_transport()
    sftp = paramiko.SFTPClient.from_transport(transport)
    host_info_filename = os.path.basename(HOST_INFO_SCRIPT_PATH)
    remote_path = REMOTE_SERVER_BASE_PATH + host_info_filename
    sftp.put(HOST_INFO_SCRIPT_PATH, remote_path)
    sftp.close()
    #Выполняем
    stdin, stdout, stderr = client.exec_command(
        REMOTE_SERVER_PYTHON_PATH + ' ' + remote_path
    )
    stdout = stdout.read()
    if stdout:
        system_info = json.loads(stdout)
        print format_data(system_info)
    else:
        print "Error getting host info"
        stderr = stderr.read()
        if stderr:
            print stderr
    client.close()
    transport.close()
