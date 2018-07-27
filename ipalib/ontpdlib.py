#
# Copyright (C) 2018  FreeIPA Contributors see COPYING for license
#
from __future__ import absolute_import

from ipaplatform.paths import paths
from ipalib.basentpconf import BaseNTPClass
from ipalib.ntpmethods import ntp_service

SERVICE_NAME = ntp_service['service']


class OpenNTPDClient(BaseNTPClass):
    def __init__(self):
        super(OpenNTPDClient, self).__init__(
            service_name=SERVICE_NAME,
            ntp_confile=paths.ONTPD_CONF,
            timeout=15,
            flag='-f',
            ntp_bin=paths.NTPD
        )


class OpenNTPDServer(BaseNTPClass):
    def __init__(self):
        super(OpenNTPDServer, self).__init__(
            service_name=SERVICE_NAME,
            ntp_confile=paths.ONTPD_CONF,
            local_srv=['127.127.1.0'],
        )
