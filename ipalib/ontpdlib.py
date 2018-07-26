#
# Copyright (C) 2018  FreeIPA Contributors see COPYING for license
#
from __future__ import absolute_import

from ipalib.basentpconf import BaseServerConfig
from ipalib.basentpconf import BaseNTPClient
from ipaplatform.paths import paths
from ipapython import ipautil


class OpenNTPDClient(BaseNTPClient):
    def __init__(self):
        super(OpenNTPDClient, self).__init__(
            path_conf=paths.ONTPD_CONF,
            ntp_bin=paths.NTPD,
            timeout=15,
            flag='-f'
        )

    def sync_time(self):
        return self.sync_ntp()


class OpenNTPDInstance(BaseServerConfig):
    def __init__(self):
        super(OpenNTPDInstance, self).__init__(
            ntp_conf=paths.ONTPD_CONF,
            local_srv="# server 127.127.1.0 iburst",
            fudge="# fudge 127.127.1.0 stratum 10",
            needopts=[{'val': '-x', 'need': False},
                      {'val': '-g', 'need': False}],
            service_name='ntpd',
        )

    def __server_mode(self):
        result = ipautil.run(['control', 'ntpd'], capture_output=True)
        self.sstore.backup_state('control', 'ntpd-mode', result.output)
        ipautil.run(['control', 'ntpd', 'server'])

    def create_instance(self):
        self._make_instance()
        try:
            self.step("set %s server mode"
                      % self.service_name,
                      self.__server_mode)
        except Exception:
            pass
        try:
            self.start_creation()
            return True
        except Exception:
            return False
