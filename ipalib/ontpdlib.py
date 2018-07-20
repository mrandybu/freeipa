#
# Copyright (C) 2018  FreeIPA Contributors see COPYING for license
#
from ipalib.basentpconf import BaseClientConfig, BaseServerConfig
from ipaplatform.paths import paths
from ipapython import ipautil

ntp_conf = """# sample ntpd configuration file, see ntpd.conf(5)

# Addresses to listen on (ntpd does not listen by default)
#listen on *
#listen on 127.0.0.1
#listen on ::1

# sync to a single server
#servers ntp.example.org

# use a random selection of 8 public stratum 2 servers
# see http://twiki.ntp.org/bin/view/Servers/NTPPoolServers
$SERVERS_BLOCK
"""

ntp_sysconfig = """# Parameters for NTP daemon.
# See ntpd(8) for more details.

# Specifies additional parameters for ntpd.
NTPD_ARGS=-s
"""
ntp_step_tickers = """# Use IPA-provided NTP server for initial time
$TICKER_SERVERS_BLOCK
"""


class OpenNTPDConfig(BaseClientConfig):
    def __init__(self):
        super(OpenNTPDConfig, self).__init__(
            ntp_conf=ntp_conf,
            ntp_sysconfig=ntp_sysconfig,
            ntp_step_tickers=ntp_step_tickers,
            path_conf=paths.ONTPD_CONF,
            ntp_bin=paths.NTPD,
        )

    def sync_time(self):
        timeout = 15
        ntp_servers = self._search_ntp_servers()
        args = [
            paths.BIN_TIMEOUT,
            str(timeout),
            self.ntp_bin,
            '-f', self.path_conf
        ]

        return self._run_sync(args, timeout, ntp_servers)


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
