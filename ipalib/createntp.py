#
# Copyright (C) 2018  FreeIPA Contributors see COPYING for license
#
import sys
from importlib import import_module


def check_import():
    impls = [['ntpd', 'NTPD'], ['ontpd', 'OpenNTPD'], ['chrony', 'Chrony']]
    for imp in impls:
        try:
            tsinst = getattr(import_module('ipalib.{srv}lib'.format(srv=imp[0])), imp[1] + 'Instance')
            tsconf = getattr(import_module('ipalib.{srv}lib'.format(srv=imp[0])), imp[1] + 'Config')
            return tsinst, tsconf, imp
        except:
            pass
    print("Package with ipa library for ntp service not found in system. "
          "Please, install library package and try again.")
    sys.exit(1)


TSINSTANCE, TSCONF, TIME_SERVICE = check_import()


def make_instance(sstore, fstore):
    cl = TSINSTANCE()
    cl.sstore = sstore
    cl.fstore = fstore
    try:
        cl.create_instance()
        return True
    except:
        return False


def sync_time(statestore=None, cli_domain=None, sysstore=None, fstore=None):
    srv_class = TSCONF()
    srv_class.statestore = statestore
    srv_class.cli_domain = cli_domain
    srv_class.sysstore = sysstore
    srv_class.fstore = fstore

    srv_class.sync_time()


def uninstall(fstore, sstore):
    srv_class = TSINSTANCE()
    srv_class.fstore = fstore
    srv_class.sstore = sstore

    srv_class.uninstall()


def restore_time_sync(statestore=None, fstore=None):
    srv_class = TSCONF()
    srv_class.statestore = statestore
    srv_class.fstore = fstore

    srv_class.check_state()
