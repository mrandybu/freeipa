#
# Copyright (C) 2018  FreeIPA Contributors see COPYING for license
#
from __future__ import absolute_import

from ipaplatform.paths import paths
from ipalib.basentpconf import BaseNTPClass
from ipalib.ntpmethods import ntp_service

SERVICE_NAME = ntp_service['service']


class ChronyClient(BaseNTPClass):
    sync_attempt_count = 3

    def __init__(self):
        super(ChronyClient, self).__init__(
            service_name=SERVICE_NAME,
            ntp_confile=paths.CHRONY_CONF,
            ntp_bin=paths.CHRONYC,
            args=[self.ntp_bin, 'waitsync',
                  str(self.sync_attempt_count), '-d']
        )


class ChronyServer(BaseNTPClass):
    def __init__(self):
        super(ChronyServer, self).__init__(
            service_name=SERVICE_NAME,
            ntp_confile=paths.CHRONY_CONF,
        )
