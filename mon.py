#!/usr/bin/env python3

import re
import os
from Exscript import Host, Account
from Exscript.protocols import SSH2, Telnet
from Exscript.protocols.drivers.nxos import NXOSDriver
from Exscript.protocols.drivers import add_driver, disable_driver
import yaml
import time


class MyNXOSDriver(NXOSDriver):
    def __init__(self):
        NXOSDriver.__init__(self)
        self.user_re = self.user_re + [re.compile(r'([^:]* )?login: ?$', re.I)]


add_driver(MyNXOSDriver)
MAIN_SECTION = 'main'

def pars_host_str(host_str):
    host_str_splited = host_str.split(':')
    host = host_str_splited[0]
    port = int(host_str_splited[1])
    return host, port


class ConnectionError(Exception):
    pass


class Device(object):
    def __init__(self, name, host, port, protocol, login, password, type_):
        self.name = name
        self.host = host
        self.port = port
        self.protocol = protocol
        self.login = login
        self.password = password
        self.type = type_

        self._exscript_host = None
        self._conn = None

    def get_uri(self):
        uri = '{protocol}://{login}@{host}'.format(**self.__dict__)
        if self.port:
            uri += ':' + str(self.port)
        return uri

    def connect(self):
        self._exscript_host = Host(uri=self.get_uri())
        self._exscript_account = Account(name=self.login, password=self.password)
        self._exscript_host.set_account(self._exscript_account)

        if self.protocol == self._exscript_host.get_protocol():
            self._conn = Telnet(debug=5)
        elif self.protocol == self._exscript_host.get_protocol():
            self._conn = SSH2()
        self._conn.set_driver(driver=self.type)
        try:
            self._conn.connect(hostname=self._exscript_host.get_address(), port=int(self._exscript_host.get_tcp_port()))
        except OSError as e:
            raise ConnectionError(str(e))

        time.sleep(5)
        self._conn.send('\r')

        self._conn.login(account=self._exscript_account)
        self._conn.autoinit()

    def show_version(self):
        self._conn.execute('show version')
        return self._conn.response

    def show_run(self):
        show_run_cmd = 'show run'
        self._conn.execute(show_run_cmd)
        conf = self._conn.response.strip()
        if conf.startswith(show_run_cmd):
            conf = conf[len(show_run_cmd):].strip()
        return conf

    def dump_show_run(self, path):
        with open(path, 'w') as cnf_:
            cnf_.write(self.show_run())


class DeviceScope(object):
    def __init__(self):
        self.scope = list()
        self.data_dir = '.'

    def load_yaml(self, path):
        with open(path) as _:
            data = yaml.load(_)

        if MAIN_SECTION in data:
            main = data.pop(MAIN_SECTION)
            self.data_dir = main.get('data', self.data_dir)

        for dev_name, dev_data in data.items():
            host, port = pars_host_str(dev_data['host'])
            dev = Device(
                name=dev_name,
                host=host, port=port,
                protocol=dev_data['protocol'],
                login=dev_data['login'],
                password=dev_data['password'],
                type_=dev_data['type']
            )
            self.scope.append(dev)

    def dump(self):
        for device in self.scope:
            device.connect()
            device.dump_show_run(path=os.path.abspath(os.path.join(self.data_dir, device.name + '.cnf')))


if __name__ == '__main__':
    scope = DeviceScope()
    scope.load_yaml('devices.yaml')
    scope.dump()
