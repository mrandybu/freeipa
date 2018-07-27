#
# Copyright (C) 2018  FreeIPA Contributors see COPYING for license
#
from __future__ import absolute_import

from ipaplatform.paths import paths
from ipalib.basentpconf import BaseNTPClass
from ipalib.ntpmethods import ntp_service

SERVICE_NAME = ntp_service['service']


class NTPDClient(BaseNTPClass):
    def __init__(self):
        super(NTPDClient, self).__init__(
            service_name=SERVICE_NAME,
            ntp_confile=paths.NTPD_CONF,
            timeout=15,
            flag='-qgc',
            ntp_bin=paths.NTPD
        )


class NTPDServer(BaseNTPClass):
    def __init__(self):
        super(NTPDServer, self).__init__(
            service_name=SERVICE_NAME,
            ntp_confile=paths.NTPD_CONF,
            local_srv=['127.127.1.0'],
            fudge={'host': '127.127.1.0', 'num': 10}
        )
