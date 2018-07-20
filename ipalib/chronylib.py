#
# Copyright (C) 2018  FreeIPA Contributors see COPYING for license
#
import os
from augeas import Augeas
from logging import getLogger

from ipapython import ipautil
from ipaplatform.tasks import tasks
from ipaplatform.paths import paths
from ipalib.basentpconf import BaseClientConfig, BaseServerConfig
from ipalib import ntpmethods
from ipalib.ntpmethods import TIME_SERVICE

logger = getLogger(__name__)


class ChronyConfig(BaseClientConfig):
    def __init__(self):
        super(ChronyConfig, self).__init__(
            path_conf=paths.CHRONY_CONF,
            ntp_bin=paths.CHRONYC
        )

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
    def __configure_chrony(sysstore, fstore, path_conf):

        if sysstore:
            sysstore.backup_state(TIME_SERVICE, "enabled",
                                  ntpmethods.service_command().is_enabled())

        aug = Augeas(flags=Augeas.NO_LOAD | Augeas.NO_MODL_AUTOLOAD,
                     loadpath=paths.USR_SHARE_IPA_DIR)

        try:
            logger.debug("Configuring %s" % TIME_SERVICE)
            chrony_conf = os.path.abspath(path_conf)
            aug.transform(TIME_SERVICE, chrony_conf)
            aug.load()
            path = '/files{path}'.format(path=chrony_conf)
            aug.remove('{}/server'.format(path))
            aug.remove('{}/pool'.format(path))
            aug.remove('{}/peer'.format(path))

            logger.debug("Backing up '%s'", chrony_conf)

            ntpmethods.backup_config(chrony_conf, fstore)

            logger.debug("Writing configuration to '%s'", chrony_conf)
            aug.save()

            logger.info('Configuration of %s was changed by installer.'
                        % TIME_SERVICE)
            configured = True

        except IOError:
            logger.error("Augeas failed to configure file %s", chrony_conf)
            configured = False

        except RuntimeError as e:
            logger.error("Configuration failed with: %s", e)
            configured = False

        finally:
            aug.close()

        tasks.restore_context(chrony_conf)
        return configured

    def sync_time(self):
        ntp_servers = self._search_ntp_servers()

        configured = False
        if ntp_servers:
            configured = self.__configure_chrony(self.statestore,
                                                 self.fstore,
                                                 self.path_conf)
        else:
            logger.warning("No SRV records of NTP servers found and "
                           "no NTP server or pool address was provided.")

        if not configured:
            print("Using default %s configuration." % TIME_SERVICE)

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

        cl.sync_time()

    def uninstall(self):
        un = BaseClientConfig()
        un.statestore = self.sstore
        un.fstore = self.fstore

        un.check_state()
