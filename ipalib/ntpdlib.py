#
# Copyright (C) 2018  FreeIPA Contributors see COPYING for license
#
from __future__ import absolute_import

from ipaplatform.paths import paths
from ipalib.basentpconf import BaseNTPClient, BaseNTPServer
from ipalib.ntpmethods import ntp_service


class NTPDClient(BaseNTPClient):
    def __init__(self):
        super(NTPDClient, self).__init__(
            ntp_confile=paths.NTPD_CONF,
            ntp_bin=paths.NTPD,
            timeout=15,
            flag='-qgc'
        )


class NTPDInstance(BaseNTPServer):
    def __init__(self):
        super(NTPDInstance, self).__init__(
            service_name=ntp_service['service'],
            ntp_confile=paths.NTPD_CONF,
            local_srv=['127.127.1.0'],
            fudge={'host': '127.127.1.0', 'num': 10},
        )
