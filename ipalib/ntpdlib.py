#
# Copyright (C) 2018  FreeIPA Contributors see COPYING for license
#
from __future__ import absolute_import

from ipalib.basentpconf import BaseClientConfig, BaseServerConfig
from ipaplatform.paths import paths
from ipapython import ipautil
from ipalib import ntpmethods

ntp_conf = """# Permit time synchronization with our time source, but do not
# permit the source to query or modify the service on this system.
restrict -4 default ignore notrust nomodify		# IPv4
restrict -6 default ignore notrust nomodify		# IPv6

# Permit all access over the loopback interface.  This could
# be tightened as well, but to do so would effect some of
# the administrative functions.
restrict 127.0.0.1
restrict ::1

# Hosts on local network are less restricted.
#restrict 192.168.1.0 mask 255.255.255.0 nomodify notrap

# Use public servers from the pool.ntp.org project.
# Please consider joining the pool (http://www.pool.ntp.org/join.html).
$SERVERS_BLOCK

#broadcast 192.168.1.255 key 42		# broadcast server
#broadcastclient			# broadcast client
#broadcast 224.0.1.1 key 42		# multicast server
#multicastclient 224.0.1.1		# multicast client
#manycastserver 239.255.254.254		# manycast server
#manycastclient 239.255.254.254 key 42	# manycast client

# Undisciplined Local Clock. This is a fake driver intended for backup
# and when no outside source of synchronized time is available.
server	127.127.1.0	# local clock
#fudge	127.127.1.0 stratum 10

# Drift file.  Put this in a directory which the daemon can write to.
# No symbolic links allowed, either, since the daemon updates the file
# by creating a temporary in the same directory and then rename()'ing
# it to the file.
driftfile /etc/ntp/drift

# Key file containing the keys and key identifiers used when operating
# with symmetric key cryptography.
keys /etc/ntp/keys

# Specify the key identifiers which are trusted.
#trustedkey 4 8 42

# Specify the key identifier to use with the ntpdc utility.
#requestkey 8

# Specify the key identifier to use with the ntpq utility.
#controlkey 8
"""

ntp_sysconfig = """OPTIONS="-x -p /var/run/ntpd.pid"

# Set to 'yes' to sync hw clock after successful ntpdate
SYNC_HWCLOCK=yes

# Additional options for ntpdate
NTPDATE_OPTIONS=""
"""
ntp_step_tickers = """# Use IPA-provided NTP server for initial time
$TICKER_SERVERS_BLOCK
"""


class NTPDConfig(BaseClientConfig):
    def __init__(self):
        super(NTPDConfig, self).__init__(
            ntp_conf=ntp_conf,
            ntp_sysconfig=ntp_sysconfig,
            ntp_step_tickers=ntp_step_tickers,
            path_conf=paths.NTPD_CONF,
            ntp_bin=paths.NTPD,
        )

    def sync_time(self):
        timeout = 15
        ntp_servers = self._search_ntp_servers()
        args = [
            paths.BIN_TIMEOUT,
            str(timeout),
            self.ntp_bin,
            '-qgc',
            self.path_conf
        ]

        return self._run_sync(args, timeout, ntp_servers)


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
