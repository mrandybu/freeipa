#
# Copyright (C) 2018  FreeIPA Contributors see COPYING for license
#
from __future__ import absolute_import

from ipaplatform.paths import paths
from ipalib.basentpconf import BaseClientConfig, BaseServerConfig
from ipalib.basentpconf import BaseNTPClient


class ChronyClient(BaseNTPClient):
    sync_attempt_count = 3

    def __init__(self):
        super(ChronyClient, self).__init__(
            path_conf=paths.CHRONY_CONF,
            ntp_bin=paths.CHRONYC,
            args=[self.ntp_bin, 'waitsync', str(self.sync_attempt_count), '-d'],
        )

    def sync_time(self):
        self.sync_ntp()


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
