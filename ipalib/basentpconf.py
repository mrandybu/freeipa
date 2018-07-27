#
# Copyright (C) 2018  FreeIPA Contributors see COPYING for license
#
from __future__ import absolute_import

import os
from logging import getLogger

from ipaplatform.tasks import tasks
from ipaplatform.paths import paths
from ipapython import ipautil

# pylint: disable=import-error,ipa-forbidden-import
from ipalib.install import sysrestore  # pylint: disable=E0611
from ipaserver.install import service
# pylint: enable=import-error,ipa-forbidden-import

from ipalib import ntpmethods
from ipalib.ntpmethods import TIME_SERVICE

logger = getLogger(__name__)


class BaseNTPClient(object):
    def __init__(self, fstore=None, ntp_confile=None, ntp_bin=None,
                 statestore=None, cli_domain=None, timeout=None, flag=None,
                 ntp_servers=None, ntp_pool=None, args=None):

        self.fstore = fstore
        self.ntp_confile = ntp_confile
        self.ntp_bin = ntp_bin
        self.statestore = statestore
        self.cli_domain = cli_domain

        self.ntp_servers = ntpmethods.search_ntp_servers(
            self.statestore,
            self.cli_domain
        )

        if not self.ntp_servers:
            self.ntp_servers = ntp_servers

        self.ntp_pool = ntp_pool
        self.timeout = timeout
        self.flag = flag
        self.args = args

        if not args:
            self.args = [paths.BIN_TIMEOUT, self.timeout,
                         self.ntp_bin, self.flag, self.ntp_confile]

    def __configure_ntp(self):
        logger.debug("Configuring {}".format(TIME_SERVICE))
        if not self.ntp_servers:
            logger.warning("No SRV records of NTP servers found and "
                           "no NTP server or pool address was provided.")

        config_content = ntpmethods.set_config(self.ntp_confile,
                                               servers=self.ntp_servers)

        logger.debug("Backing up {}".format(self.ntp_confile))
        ntpmethods.backup_config(self.ntp_confile, self.fstore)

        logger.debug("Backing up state {}".format(TIME_SERVICE))

        enabled = ntpmethods.ntp_service['api'].is_enabled()
        running = ntpmethods.ntp_service['api'].is_running()

        self.statestore.backup_state(ntpmethods.ntp_service['service'],
                                     'enabled', enabled)
        self.statestore.backup_state(ntpmethods.ntp_service['service'],
                                     'running', running)

        logger.debug("Writing configuration to {}".format(self.ntp_confile))
        ntpmethods.ntp_service['api'].stop()
        ntpmethods.write_config(self.ntp_confile, config_content)

        tasks.restore_context(self.ntp_confile)

    def sync_time(self):
        configured = False

        try:
            self.__configure_ntp()
            configured = True
        except Exception:
            pass

        if not configured:
            logger.info("Using default {} configuration".format(TIME_SERVICE))

        if not os.path.exists(self.ntp_bin):
            return False

        try:
            logger.info("Attempting to sync time with {}".format(TIME_SERVICE))
            logger.info("Will timeout after {} seconds".format(self.timeout))

            ipautil.run(self.args)

            ntpmethods.ntp_service['api'].enable()
            ntpmethods.ntp_service['api'].start()

            return True

        except ipautil.CalledProcessError as e:
            if e.returncode == 124:
                logger.debug("Process did not complete before timeout")

            return False

    def uninstall(self):
        ntpmethods.uninstall(self.statestore, self.fstore,
                             self.ntp_confile, logger)


class BaseNTPServer(service.Service):
    def __init__(self, service_name, ntp_confile=None, fstore=None,
                 ntp_servers=None, ntp_pool=None, local_srv=None,
                 fudge=None, sstore=None):
        super(BaseNTPServer, self).__init__(
            service_name=service_name,
            fstore=fstore,
            service_desc="NTP daemon",
            sstore=sstore,
        )

        self.ntp_confile = ntp_confile
        self.ntp_servers = ntp_servers
        self.ntp_pool = ntp_pool
        self.local_srv = local_srv
        self.fudge = fudge

        if not self.fstore:
            self.fstore = sysrestore.FileStore(paths.SYSRESTORE)

    def __configure_ntp(self):
        logger.debug("Make backup")
        self.fstore.backup_file(self.ntp_confile)

        logger.debug("Configuring")
        content = ntpmethods.set_config(self.ntp_confile,
                                        servers=self.local_srv,
                                        fudge=self.fudge)

        logger.debug("Write config")

        ntpmethods.ntp_service['api'].stop()
        ntpmethods.write_config(self.ntp_confile, content)

    def sync_time(self):
        self.step("stopping %s" % self.service_name, self.stop)
        self.step("writing configuration", self.__configure_ntp)
        self.step("configuring %s to start on boot"
                  % self.service_name, self.enable)
        self.start("starting %d" % self.service_name, self.start)

        self.start_creation()

    def uninstall(self):
        ntpmethods.uninstall(
            self.sstore, self.fstore, self.ntp_confile, logger
        )
