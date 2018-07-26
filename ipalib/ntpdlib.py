#
# Copyright (C) 2018  FreeIPA Contributors see COPYING for license
#
from __future__ import absolute_import

from ipalib.basentpconf import BaseServerConfig
from ipalib.basentpconf import BaseNTPClient
from ipaplatform.paths import paths
from ipapython import ipautil
from ipalib import ntpmethods


class NTPDClient(BaseNTPClient):
    def __init__(self):
        super(NTPDClient, self).__init__(
            path_conf=paths.NTPD_CONF,
            ntp_bin=paths.NTPD,
            timeout=15,
            flag='-qgc'
        )

    def sync_time(self):
        return self.sync_ntp()


class NTPDInstance(BaseServerConfig):
    def __init__(self):
        self.ntp_bin = paths.NTPD
        self.path_conf = paths.NTPD_CONF

        super(NTPDInstance, self).__init__(
            ntp_conf=paths.NTPD_CONF,
            local_srv="server 127.127.1.0 iburst",
            fudge="fudge 127.127.1.0 stratum 10",
            needopts=[{'val': '-x', 'need': True},
                      {'val': '-g', 'need': True}],
            service_name='ntpd'
        )

    def create_instance(self):
        timeout = 15

        self._make_instance()
        self.start_creation()

        ntpmethods.service_command().stop()
        args = [
            paths.BIN_TIMEOUT,
            str(timeout),
            self.ntp_bin,
            '-qgc',
            self.path_conf
        ]
        ipautil.run(args)
        ntpmethods.service_command().start()
