#
# Copyright (C) 2018  FreeIPA Contributors see COPYING for license
#
from __future__ import absolute_import

import os
from logging import getLogger

from ipaplatform.tasks import tasks
from ipaplatform.paths import paths
from ipaplatform.constants import constants
from ipapython.ipautil import CalledProcessError
from ipapython import ipautil

# pylint: disable=import-error,ipa-forbidden-import
from ipaclient.install import ipadiscovery  # pylint: disable=E0611
from ipalib.install import sysrestore  # pylint: disable=E0611
from ipaserver.install import service
# pylint: enable=import-error,ipa-forbidden-import

from ipalib import ntpmethods
from ipalib.ntpmethods import TIME_SERVICE

NTPD_OPTS_VAR = constants.NTPD_OPTS_VAR
NTPD_OPTS_QUOTE = constants.NTPD_OPTS_QUOTE

logger = getLogger(__name__)


class BaseClientConfig(object):
    def __init__(self, fstore=None, ntp_conf=None, ntp_sysconfig=None,
                 ntp_step_tickers=None, sysstore=None,
                 path_conf=None, ntp_bin=None, statestore=None,
                 cli_domain=None):

        self.fstore = fstore
        self.ntp_conf = ntp_conf
        self.ntp_sysconfig = ntp_sysconfig
        self.ntp_step_tickers = ntp_step_tickers
        self.sysstore = sysstore
        self.path_conf = path_conf
        self.ntp_bin = ntp_bin
        self.statestore = statestore
        self.cli_domain = cli_domain

    def __config_ntp(self, ntp_servers):
        if self.statestore:
            self.sysstore = self.statestore

        path_step_tickers = paths.NTP_STEP_TICKERS
        path_ntp_sysconfig = paths.SYSCONFIG_NTPD
        sub_dict = {}
        sub_dict["SERVERS_BLOCK"] = "\n".join(
            "server %s" % s for s in ntp_servers
        )
        sub_dict["TICKER_SERVERS_BLOCK"] = "\n".join(ntp_servers)

        nc = ipautil.template_str(self.ntp_conf, sub_dict)
        config_step_tickers = False

        if os.path.exists(path_step_tickers):
            config_step_tickers = True
            ns = ipautil.template_str(self.ntp_step_tickers, sub_dict)
            ntpmethods.backup_config(path_step_tickers, self.fstore)
            ntpmethods.write_config(path_step_tickers, ns)
            tasks.restore_context(path_step_tickers)

        if self.sysstore:
            module = 'ntp'
            self.sysstore.backup_state(
                module,
                "enabled",
                ntpmethods.service_command().is_enabled()
            )
            if config_step_tickers:
                self.sysstore.backup_state(module, "step-tickers", True)

        ntpmethods.backup_config(self.path_conf, self.fstore)
        ntpmethods.write_config(self.path_conf, nc)
        tasks.restore_context(self.path_conf)

        ntpmethods.backup_config(path_ntp_sysconfig, self.fstore)
        ntpmethods.write_config(path_ntp_sysconfig, self.ntp_sysconfig)
        tasks.restore_context(path_ntp_sysconfig)

        ntpmethods.service_command().stop()

    def _run_sync(self, args, timeout, ntp_servers):

        configured = False

        if ntp_servers:
            try:
                self.__config_ntp(ntp_servers)
                configured = True
            except Exception:
                pass
        else:
            logger.warning("No SRV records of NTP servers found and "
                           "no NTP server or pool address was provided.")

        if not configured:
            logger.info("Using default %s configuration.", TIME_SERVICE)

        if not os.path.exists(self.ntp_bin):
            return False

        try:
            logger.info("Attempting to sync time using %s.", TIME_SERVICE)
            logger.info("Will timeout after %s seconds", timeout)
            ipautil.run(args)
            ntpmethods.service_command().start()
            return True
        except ipautil.CalledProcessError as e:
            if e.returncode == 124:
                logger.debug("Process did not complete before timeout")
            return False

    def _search_ntp_servers(self):
        logger.info('Synchronizing time')
        ntpmethods.force_service(self.statestore)
        ds = ipadiscovery.IPADiscovery()
        ntp_servers = ds.ipadns_search_srv(
            self.cli_domain,
            '_ntp._udp',
            None, False
        )
        return ntp_servers

    def check_state(self):

        ts = TIME_SERVICE
        if ts in ('ntpd', 'openntpd'):
            ts = 'ntp'

        if self.statestore.has_state(ts):
            srv_enabled = self.statestore.restore_state(ts, 'enabled')
            restored = False

            try:
                restored = self.fstore.restore_file(self.path_conf)
                if self.ntp_sysconfig:
                    restored |= self.fstore.restore_file(paths.SYSCONFIG_NTPD)
                if self.ntp_step_tickers:
                    srv_enabled_tickers = self.statestore.restore_state(
                        ts,
                        'step-tickers'
                    )
                    if srv_enabled_tickers:
                        restored |= self.fstore.restore_file(
                            paths.NTP_STEP_TICKERS
                        )
            except Exception:
                pass

            if not srv_enabled:
                ntpmethods.service_command().stop()
                ntpmethods.service_command().disable()
            elif restored:
                ntpmethods.service_command().restart()

        try:
            ntpmethods.restore_forced_service(self.statestore)
        except CalledProcessError as e:
            logger.error("Failed to restore time synchronization service "
                         "%s", e)


class BaseServerConfig(service.Service):
    def __init__(self, fstore=None, ntp_conf=None,
                 local_srv=None, fudge=None, needopts=None, service_name=None):

        self.ntp_conf = ntp_conf
        self.local_srv = local_srv
        self.fudge = fudge
        self.needopts = needopts
        self.service_name = service_name

        if fstore:
            self.fstore = fstore
        else:
            self.fstore = sysrestore.FileStore(paths.SYSRESTORE)

        super(BaseServerConfig, self).__init__(
            service_name,
            service_desc="NTP daemon",
        )

    def __write_config(self):

        self.fstore.backup_file(self.ntp_conf)
        self.fstore.backup_file(paths.SYSCONFIG_NTPD)

        ntpconf = []
        fd = open(self.ntp_conf, "r")
        for line in fd:
            opt = line.split()
            if len(opt) < 2:
                ntpconf.append(line)
                continue
            if opt[0] == "server" and opt[1] == self.local_srv:
                line = ""
            elif opt[0] == "fudge":
                line = ""
            ntpconf.append(line)

        with open(self.ntp_conf, "w") as fd:
            for line in ntpconf:
                fd.write(line)
            fd.write("\n### Added by IPA Installer ###\n")
            fd.write("{}\n".format(self.local_srv))
            fd.write("{}\n".format(self.fudge))

        fd = open(paths.SYSCONFIG_NTPD, "r")
        lines = fd.readlines()
        fd.close()

        for line in lines:
            sline = line.strip()
            if not sline.startswith(NTPD_OPTS_VAR):
                continue
            sline = sline.replace(NTPD_OPTS_QUOTE, '')
            for opt in self.needopts:
                if sline.find(opt['val']) != -1:
                    opt['need'] = False

        newopts = []
        for opt in self.needopts:
            if opt['need']:
                newopts.append(opt['val'])

        done = False
        if newopts:
            fd = open(paths.SYSCONFIG_NTPD, "w")
            for line in lines:
                if not done:
                    sline = line.strip()
                    if not sline.startswith(NTPD_OPTS_VAR):
                        fd.write(line)
                        continue
                    sline = sline.replace(NTPD_OPTS_QUOTE, '')
                    (_variable, opts) = sline.split('=', 1)
                    fd.write(NTPD_OPTS_VAR + '="%s %s"\n'
                             % (opts, ' '.join(newopts))
                             )
                    done = True
                else:
                    fd.write(line)
            fd.close()

    def __stop(self):
        self.backup_state("running", self.is_running())
        self.stop()

    def __start(self):
        self.start()

    def __enable(self):
        self.backup_state("enabled", self.is_enabled())
        self.enable()

    def _make_instance(self):
        self.step("stopping %s" % self.service_name, self.__stop)
        self.step("writing configuration", self.__write_config)
        self.step("configuring %s to start on boot" % self.service_name,
                  self.__enable)
        self.step("starting %s" % self.service_name, self.__start)

    def create_instance(self):
        self._make_instance()
        self.start_creation()

    def uninstall(self):
        if self.is_configured():
            self.print_msg("Unconfiguring %s" % self.service_name)

        running = self.restore_state("running")
        enabled = self.restore_state("enabled")

        self.stop()
        self.disable()

        try:
            self.fstore.restore_file(self.ntp_conf)
        except ValueError as error:
            logger.debug("%s", error)

        if enabled:
            self.enable()
        if running:
            self.restart()
