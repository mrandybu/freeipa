#
# Copyright (C) 2018  FreeIPA Contributors see COPYING for license
#
from __future__ import absolute_import

from ipaplatform.paths import paths
from ipalib.basentpconf import BaseNTPClient, BaseNTPServer
from ipalib.ntpmethods import ntp_service


class ChronyClient(BaseNTPClient):
    sync_attempt_count = 3

    def __init__(self):
        super(ChronyClient, self).__init__(
            ntp_confile=paths.CHRONY_CONF,
            ntp_bin=paths.CHRONYC,
            args=[self.ntp_bin, 'waitsync',
                  str(self.sync_attempt_count), '-d'],
        )


class ChronyInstance(BaseNTPServer):
    def __init__(self):
        super(ChronyInstance, self).__init__(
            service_name=ntp_service['service'],
            ntp_confile=paths.CHRONY_CONF,
        )
