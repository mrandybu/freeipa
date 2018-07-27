#
# Copyright (C) 2018  FreeIPA Contributors see COPYING for license
#
from __future__ import print_function

import sys
from importlib import import_module


def detect_ntp_daemon():
    impls = [['ntpd', 'NTPD'], ['ontpd', 'OpenNTPD'], ['chrony', 'Chrony']]
    for imp in impls:
        try:
            tsinst = getattr(import_module(
                'ipalib.{srv}lib'.format(srv=imp[0])),
                imp[1] + 'Instance')
            tsconf = getattr(import_module(
                'ipalib.{srv}lib'.format(srv=imp[0])),
                imp[1] + 'Config')
            return tsinst, tsconf, imp
        except Exception:
            pass
    print("Package with ipa library for ntp service not found in system. "
          "Please, install library package and try again.")
    sys.exit(1)


NTPSERVER, NTPCLIENT, TIME_SERVICE = detect_ntp_daemon()


def sync_time_server(fstore, sstore, ntp_servers, ntp_pool):
    cl = NTPSERVER()

    cl.fstore = fstore
    cl.sstore = sstore
    cl.ntp_servers = ntp_servers
    cl.ntp_pool = ntp_pool
    cl.ntp_pool = ntp_pool

    try:
        cl.sync_time()
        return True
    except Exception:
        return False


def sync_time_client(fstore, statestore, cli_domain, ntp_servers, ntp_pool):
    cl = NTPCLIENT()

    cl.fstore = fstore
    cl.statestore = statestore
    cl.cli_domain = cli_domain
    cl.ntp_servers = ntp_servers
    cl.ntp_pool = ntp_pool

    return cl.sync_time()


def uninstall_server(fstore, sstore):
    cl = NTPSERVER()

    cl.sstore = sstore
    cl.fstore = fstore

    cl.uninstall()


def uninstall_client(fstore, sstore):
    cl = NTPCLIENT()

    cl.sstore = sstore
    cl.fstore = fstore

    cl.uninstall()
