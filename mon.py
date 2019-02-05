#!/usr/bin/env python3
"""
Main file for running configurate monitor
"""

import logging
import os
import re
import tempfile
import time
import sys
import argparse
import urllib.request

import diffios
import yaml
from Exscript import Host, Account
from Exscript.protocols import SSH2, Telnet
from Exscript.protocols.drivers import add_driver
from Exscript.protocols.drivers.ios import IOSDriver
from Exscript.protocols.drivers.ios_xr import IOSXRDriver
from Exscript.protocols.drivers.nxos import NXOSDriver
from Exscript.protocols.exception import ProtocolException, TimeoutException
from brigit import Git

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class MyNXOSDriver(NXOSDriver):
    """Driver for NXOS devices"""
    def __init__(self):
        NXOSDriver.__init__(self)
        self.user_re = self.user_re + [re.compile(r'([^:]* )?login: ?$', re.I)]


class MyIOSDriver(IOSDriver):
    """Driver for IOS devices"""
    def __init__(self):
        IOSDriver.__init__(self)
        self.user_re = self.user_re + [re.compile(r'([^:]* )?login: ?$', re.I)]


class MyIOSXRDriver(IOSXRDriver):
    """Driver for IOS XR devices"""
    def __init__(self):
        IOSXRDriver.__init__(self)
        self.user_re = self.user_re + [re.compile(r'([^:]* )?login: ?$', re.I)]


add_driver(MyNXOSDriver)
add_driver(MyIOSDriver)
add_driver(MyIOSXRDriver)
MAIN_SECTION = 'main'


def pars_host_str(host_str):
    """Parsing host string from config"""
    host_str_splited = host_str.split(':')
    host = host_str_splited[0]
    port = int(host_str_splited[1])
    return host, port


class DevConnectionError(Exception):
    """Pass connect error exception"""
    pass


class Device(object):
    """Device class for implement main device functionality"""
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

        self.tempfile = tempfile.NamedTemporaryFile(delete=False)

    def get_uri(self):
        """Get url for connect"""
        uri = '{protocol}://{login}@{host}'.format(**self.__dict__)
        if self.port:
            uri += ':' + str(self.port)
        return uri

    def connect(self):
        """Function for connecting to device"""
        logger.warning('start connecting to {}'.format(self.get_uri()))
        self._exscript_host = Host(uri=self.get_uri())
        self._exscript_account = Account(name=self.login, password=self.password)
        self._exscript_host.set_account(self._exscript_account)

        if self.protocol == self._exscript_host.get_protocol():
            self._conn = Telnet(debug=0)
        elif self.protocol == self._exscript_host.get_protocol():
            self._conn = SSH2()
        self._conn.set_driver(driver=self.type)
        try:
            self._conn.connect(hostname=self._exscript_host.get_address(), port=int(self._exscript_host.get_tcp_port()))
            logger.warning('connection established with {}'.format(self.get_uri()))
        except OSError as e:
            raise DevConnectionError('{} {}'.format(self.get_uri(), str(e)))

        time.sleep(5)
        self._conn.send('\r')
        logger.warning('start login to {}'.format(self.get_uri()))
        self._conn.login(account=self._exscript_account)
        logger.warning('login to {} success'.format(self.get_uri()))
        self._conn.autoinit()

    def exit(self):
        """Exit from router after finishing"""
        self._conn.send('exit\r')

    def show_version(self):
        """Return version info from device"""
        self._conn.execute('show version')
        return self._conn.response

    def show_run(self):
        """Return running config from device"""
        show_run_cmd = 'show run'
        self._conn.execute(show_run_cmd)
        conf = self._conn.response.strip()
        if conf.startswith(show_run_cmd):
            conf = conf[len(show_run_cmd):].strip()
        return conf

    def dump_show_run(self, path):
        """Write config file from device"""
        logger.warning('Start dumping show run {} to "{}" file'.format(self.get_uri(), path))
        with open(path, 'w') as cnf_:
            cnf_.write(self.show_run())
        logger.warning('show run {} dumped to "{}" file success'.format(self.get_uri(), path))

    def dump_config(self, path):
        """Write config into tempfile"""
        logger.warning('Start backup previous config file {}'.format(path))
        if os.path.exists(path):
            with open(path, 'rb') as src, self.tempfile as temp:
                temp.write(src.read())
        else:
            logger.warning('Nothing to backup.')


class DeviceScope(object):
    """Class for implement devices"""
    def __init__(self):
        self.scope = list()
        self.data_dir = '.'
        self.main = None

    def load_yaml(self, path):
        """Testbed devices"""
        logger.warning('loading config "{}"'.format(path))
        if isinstance(path, str):
            with open(path) as _:
                data = yaml.load(_)
        elif hasattr(path.read) and hasattr(path.name):
            data = yaml.load(path)
        else:
            raise TypeError('argument path should be path or file like object')

        logger.warning('config "{}" loaded success'.format(path))
        if MAIN_SECTION in data:
            logger.warning('detected main in config {}'.format(path))
            self.main = data.pop(MAIN_SECTION)
            self.data_dir = self.main.get('data', {}).get('path', self.data_dir)

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
        """Make dumps and commits to git if necessary"""
        git_remote = self.main['data']['git_remote']
        git_branch = self.main['data']['git_branch']
        git = Git(self.data_dir, remote=git_remote)
        git.checkout(git_branch)
        updated_devices = []
        for device in self.scope:
            try:
                device.connect()
                conf_name = device.name + '.cnf'
                dump_path = os.path.abspath(os.path.join(self.data_dir, conf_name))
                device.dump_config(path=dump_path)
                device.dump_show_run(path=dump_path)
                device.exit()
            except DevConnectionError as e:
                logger.error(e)
            except (ProtocolException, TimeoutException) as e:
                logger.error('{} {}'.format(device.get_uri(), e))

            # TODO: to be fixed in next version exscript
            except UnboundLocalError:
                logger.error('Connection refused {}'.format(device.get_uri()))
            else:
                diffs = diffios.Compare(device.tempfile.name, dump_path)
                if diffs.additional():
                    logger.warning(diffs.delta())
                    git.add(conf_name)
                    updated_devices.append(device.name)
                else:
                    logger.error("Nothing changed in config {}.cnf".format(device.name))

        if updated_devices:
            git.commit(message="Devices {} were updated".format(updated_devices))
            git.push()
            logger.warning("Changes pushed to remote git {}".format(git_remote))


def pars(argv_):
    parser = argparse.ArgumentParser(description='Utilite for monitorung cisco devices')
    parser.add_argument('config', type=str,
                        help='path to yaml file in format http://domain/urlpath for config on http server '
                             'or path/path fol local stored file')

    return parser.parse_args(argv_)


def main(argv_):
    args = pars(argv_)
    config_path = args.config
    scope = DeviceScope()
    if config_path.startswith('http://') or config_path.startswith('https://'):
        with urllib.request.urlopen(config_path) as response:
            scope.load_yaml(response)
    else:
        scope.load_yaml(config_path)
    scope.dump()


if __name__ == '__main__':
    main(sys.argv[1:])
