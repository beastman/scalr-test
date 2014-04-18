#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
from subprocess import Popen, PIPE
import json


class HostInfoGetter(object):
    PARTITIONS_DEVICE_NAME_RE = re.compile('(\S+)$')
    GET_PACKAGES_COMMAND_UBUNTU = 'dpkg --get-selections'
    RELEASE_ISSUE_PATH = '/etc/issue'

    def __init__(self):
        self._check_compatibility()

    def _check_compatibility(self):
        uname = Popen('uname -a', shell=True, stdout=PIPE).stdout.read()
        if os.path.exists(self.RELEASE_ISSUE_PATH):
            #На всякий случай, добавляем содержимое /etc/issue
            issue_file = open(self.RELEASE_ISSUE_PATH)
            uname += issue_file.read()
            issue_file.close()
        uname = uname.lower()
        if 'debian' not in uname and 'ubuntu' not in uname:
            raise Exception('For now this class only supports Debian and Ubuntu Linux')

    def load_average(self):
        return os.getloadavg()

    def get_block_device_names(self):
        data = Popen(
            "cat /proc/partitions | awk '{print $4}'", shell=True, stdout=PIPE
        ).stdout.read()
        if data.startswith('name'):
            data = data[4:]
        data = data.strip()
        return data.split('\n')

    def get_cpu_cores(self):
        #TODO: Данная реализация вернет неверные данные,
        # если процессоров в системе больше одного.
        data = Popen(
            "cat /proc/cpuinfo | grep 'cpu cores' | tail -1 | sed -e 's/[^0-9]//g'",
            shell=True, stdout=PIPE
        ).stdout.read()
        return data.strip()

    def _get_df_info(self):
        result = []
        df_out = Popen('df -h', shell=True, stdout=PIPE).stdout.read()
        df_out = df_out.strip()
        for line in df_out.split('\n'):
            groups = re.findall(r'(\S+)', line)
            if groups[0] == 'Filesystem':
                continue
            elif len(groups) != 6:
                raise Exception('df returned unsupported output')
            else:
                result.append({
                    'fs_name': groups[0],
                    'size': groups[1],
                    'used': groups[2],
                    'available': groups[3],
                    'usage_percent': groups[4],
                    'mount_point': groups[5],
                })
        return result

    def get_mount_points(self):
        result = {}
        df_info = self._get_df_info()
        for row in df_info:
            result[row['mount_point']] = row['fs_name']
        return result

    def get_rootfs_free_space(self):
        result = None
        df_info = self._get_df_info()
        for row in df_info:
            if row['mount_point'] == '/':
                result = row['available']
                break
        return result

    def get_installed_packages(self):
        result = []
        #Здесь может быть какой-то код для определения дистрибутива,
        # пока что предполагаем, что это Ubuntu(dpkg)
        dpkg_out = Popen(
            self.GET_PACKAGES_COMMAND_UBUNTU, shell=True, stdout=PIPE
        ).stdout.read()
        dpkg_out = dpkg_out.strip()
        for row in dpkg_out.split('\n'):
            package_name = row.strip()
            groups = re.match(r'(\S+)\s+(\w+)$', package_name).groups()
            if groups[1] == 'install':
                result.append(groups[0])
        return result


if __name__ == "__main__":
    info_getter = HostInfoGetter()
    system_info = {
        'load_average': info_getter.load_average(),
        'block_device_names': info_getter.get_block_device_names(),
        'cpu_cores': info_getter.get_cpu_cores(),
        'mount_points': info_getter.get_mount_points(),
        'rootfs_free_space': info_getter.get_rootfs_free_space(),
        'installed_packages': info_getter.get_installed_packages(),
    }
    print json.dumps(system_info)