#
# Copyright (C) 2018  FreeIPA Contributors see COPYING for license
#
from __future__ import absolute_import

from ipalib.basentpconf import BaseNTPClient, BaseNTPServer
from ipalib.ntpmethods import ntp_service
from ipaplatform.paths import paths


class OpenNTPDClient(BaseNTPClient):
    def __init__(self):
        super(OpenNTPDClient, self).__init__(
            ntp_confile=paths.ONTPD_CONF,
            ntp_bin=paths.NTPD,
            timeout=15,
            flag='-f'
        )

    def sync_time(self):
        return self.sync_ntp()


class OpenNTPDServer(BaseNTPServer):
    def __init__(self):
        super(OpenNTPDServer, self).__init__(
            service_name=ntp_service['service'],
            ntp_confile=paths.ONTPD_CONF,
            local_srv=['127.127.1.0'],
        )

    def create_instance(self):
        self.make_instance()
