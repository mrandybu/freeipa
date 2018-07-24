#
# Copyright (C) 2018  FreeIPA Contributors see COPYING for license
#
from __future__ import absolute_import

import os
from logging import getLogger

from ipapython import ipautil
from ipaplatform.tasks import tasks
from ipaplatform.paths import paths
from ipalib.basentpconf import BaseClientConfig, BaseServerConfig
from ipalib import ntpmethods
from ipalib.ntpmethods import TIME_SERVICE

logger = getLogger(__name__)


class ChronyConfig(BaseClientConfig):
    def __init__(self, ntp_servers=None, ntp_pool=None):
        super(ChronyConfig, self).__init__(
            path_conf=paths.CHRONY_CONF,
            ntp_bin=paths.CHRONYC
        )

        self.ntp_servers = ntp_servers
        self.ntp_pool = ntp_pool

    def __sync_chrony(self):

        ntpmethods.service_command().enable()

        ntpmethods.service_command().restart()

        sync_attempt_count = 3
        args = [self.ntp_bin, 'waitsync', str(sync_attempt_count), '-d']

        try:
            logger.info('Attempting to sync time with chronyc.')
            ipautil.run(args)
            logger.info('Time synchronization was successful.')
            return True

        except ipautil.CalledProcessError:
            logger.warning('Process chronyc waitsync failed to sync time!')
            logger.warning(
                "Unable to sync time with chrony server, assuming the time "
                "is in sync. Please check that 123 UDP port is opened, "
                "and any time server is on network.")
            return False

    @staticmethod
    def __configure_chrony(sysstore, fstore, path_conf,
                           ntp_servers=None, ntp_pool=None):

        if sysstore:
            sysstore.backup_state(TIME_SERVICE, "enabled",
                                  ntpmethods.service_command().is_enabled())

        try:
            chrony_conf = os.path.abspath(path_conf)

            logger.debug("Configuring %s", TIME_SERVICE)

            conf_content = ntpmethods.parse_config(chrony_conf,
                                                   ntp_pool, ntp_servers)

            logger.debug("Backing up %s", chrony_conf)

            ntpmethods.backup_config(chrony_conf, fstore)

            logger.debug("Writing configuration to %s", chrony_conf)
            ntpmethods.write_config(chrony_conf, conf_content)

            logger.info('Configuration of %s was changed by installer.',
                        TIME_SERVICE)
            configured = True

        except IOError:
            logger.error("Failed to configure file %s", chrony_conf)
            configured = False

        except RuntimeError as e:
            logger.error("Configuration failed with: %s", e)
            configured = False

        tasks.restore_context(chrony_conf)
        return configured

    def sync_time(self):

        ntp_servers = self.ntp_servers
        if not ntp_servers:
            ntp_servers = self._search_ntp_servers()

        configured = False
        if ntp_servers | self.ntp_pool:
            configured = self.__configure_chrony(self.statestore,
                                                 self.fstore,
                                                 self.path_conf,
                                                 self.ntp_servers,
                                                 self.ntp_pool)
        else:
            logger.warning("No SRV records of NTP servers found and "
                           "no NTP server or pool address was provided.")

        if not configured:
            logger.info("Using default %s configuration.", TIME_SERVICE)

        return self.__sync_chrony()


class ChronyInstance(BaseServerConfig):
    def __init__(self):
        super(ChronyInstance, self).__init__(
            service_name='chronyd'
        )

    def create_instance(self):
        cl = ChronyConfig()
        cl.statestore = self.sstore
        cl.fstore = self.fstore
        cl.ntp_servers = self.ntp_servers
        cl.ntp_pool = self.ntp_pool

        cl.sync_time()

    def uninstall(self):
        un = BaseClientConfig()
        un.statestore = self.sstore
        un.fstore = self.fstore

        un.check_state()
