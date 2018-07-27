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


class BaseNTPClass(service.Service):
    def __init__(self, service_name, fstore=None, sstore=None,
                 ntp_confile=None, ntp_servers=None, ntp_pool=None,
                 local_srv=None, fudge=None, cli_domain=None, timeout=None,
                 flag=None, args=None, ntp_bin=None):
        super(BaseNTPClass, self).__init__(
            service_name=service_name,
            fstore=fstore,
            sstore=sstore,
            service_desc="NTP daemon",
        )

        self.ntp_confile = ntp_confile
        self.ntp_servers = ntp_servers
        self.ntp_bin = ntp_bin
        self.ntp_pool = ntp_pool

        if not self.ntp_servers and not self.ntp_pool:
            self.ntp_servers = ntpmethods.search_ntp_servers(self.sstore,
                                                             self.cli_domain)

        self.local_srv = local_srv
        self.fudge = fudge
        self.cli_domain = cli_domain
        self.timeout = timeout
        self.flag = flag
        self.args = args

        if not args:
            self.args = [paths.BIN_TIMEOUT, self.timeout,
                         self.ntp_bin, self.flag, self.ntp_confile]

        if not self.fstore:
            sysrestore.FileStore(paths.SYSRESTORE)

    def __configure_ntp(self):
        logger.debug("Configuring %s", TIME_SERVICE)

        if self.ntp_servers or self.ntp_pool:
            config_content = ntpmethods.set_config(
                self.ntp_confile, self.ntp_pool, self.ntp_servers)
        elif self.local_srv:
            config_content = ntpmethods.set_config(
                self.ntp_confile, servers=self.local_srv, fudge=self.fudge)
        else:
            config_content = None
            logger.warning("No SRV records of NTP servers found and "
                           "no NTP server or pool address was provided.")
            logger.info("Using default %s configuration", TIME_SERVICE)

        logger.debug("Backing up state %s", TIME_SERVICE)

        enabled = ntpmethods.is_enabled()
        running = ntpmethods.is_running()

        self.sstore.backup_state(
            ntpmethods.ntp_service['service'], 'enabled', enabled)
        self.sstore.backup_state(
            ntpmethods.ntp_service['service'], 'running', running)

        ntpmethods.ntp_service['api'].stop()

        if not config_content:
            return False

        logger.debug("Backing up %s", self.ntp_confile)
        ntpmethods.backup_config(self.ntp_confile, self.fstore)

        logger.debug("Writing configuration to %s", self.ntp_confile)
        ntpmethods.write_config(self.ntp_confile, config_content)

        tasks.restore_context(self.ntp_confile)

        return True

    def sync_time(self):

        if not self.__configure_ntp():
            ntpmethods.service_control.print_msg(
                "Using default %s configuration", TIME_SERVICE)
        else:
            ntpmethods.service_control.print_msg(
                "Successfully configuring %s", TIME_SERVICE)

        if self.ntp_bin:
            if not os.path.exists(self.ntp_bin):
                return False

        if self.args:
            try:
                logger.info("Attempting to sync time with %s", TIME_SERVICE)
                logger.info("Will timeout after %s seconds", TIME_SERVICE)

                ipautil.run(self.args)

                ntpmethods.ntp_service['api'].enable()
                ntpmethods.ntp_service['api'].start()

                return True

            except ipautil.CalledProcessError as e:
                if e.returncode == 124:
                    logger.debug("Process did not complete before timeout")

                return False

        try:
            self.step("stopping %s" % self.service_name, self.stop)
            self.step("writing configuration", self.__configure_ntp)
            self.step("configuring %s to start on boot"
                      % self.service_name, self.enable)
            self.start("starting %d" % self.service_name, self.start)

            self.start_creation()

            return True
        except Exception:
            return False

    def uninstall(self):
        ntpmethods.uninstall(
            self.sstore, self.fstore, self.ntp_confile, logger)
