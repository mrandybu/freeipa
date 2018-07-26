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
from ipalib.install import sysrestore  # pylint: disable=E0611
from ipaserver.install import service
# pylint: enable=import-error,ipa-forbidden-import

from ipalib import ntpmethods
from ipalib.ntpmethods import TIME_SERVICE

NTPD_OPTS_VAR = constants.NTPD_OPTS_VAR
NTPD_OPTS_QUOTE = constants.NTPD_OPTS_QUOTE

logger = getLogger(__name__)


class BaseNTPClient(object):
    def __init__(self, fstore=None, path_conf=None, ntp_bin=None, statestore=None,
                 cli_domain=None, timeout=None, flag=None, ntp_servers=None, ntp_pool=None, args=None):
        self.fstore = fstore
        self.ntp_confile = path_conf
        self.ntp_bin = ntp_bin
        self.statestore = statestore
        self.cli_domain = cli_domain

        self.ntp_servers = ntpmethods.search_ntp_servers(
            self.statestore,
            self.cli_domain
        )

        if not self.ntp_servers:
            self.ntp_servers = ntp_servers

        self.ntp_pool = ntp_pool
        self.timeout = timeout
        self.flag = flag
        self.args = args

        if not args:
            self.args = [paths.BIN_TIMEOUT, self.timeout,
                         self.ntp_bin, self.flag, self.ntp_confile]

    def __configure_ntp(self):
        logger.debug("Configuring {}".format(TIME_SERVICE))
        if not self.ntp_servers:
            logger.warning("No SRV records of NTP servers found and "
                           "no NTP server or pool address was provided.")

        content = ntpmethods.set_config(path=self.ntp_confile, servers=self.ntp_servers)
        logger.debug("Backing up {}".format(self.ntp_confile))

        ntpmethods.backup_config(self.ntp_confile, self.fstore)
        logger.debug("Writing configuration to {}".format(self.ntp_confile))

        ntpmethods.service_command()['srv_api'].stop()
        ntpmethods.write_config(self.ntp_confile, content)

        tasks.restore_context(self.ntp_confile)

    def sync_ntp(self):
        configured = False

        try:
            self.__configure_ntp()
            configured = True
        except Exception:
            pass

        if not configured:
            logger.info("Using default {} configuration".format(TIME_SERVICE))

        if not os.path.exists(self.ntp_bin):
            return False

        try:
            logger.info("Attempting to sync time with {}".format(TIME_SERVICE))
            logger.info("Will timeout after {} seconds".format(self.timeout))

            ipautil.run(self.args)

            ntpmethods.service_command()['srv_api'].enable()
            ntpmethods.service_command()['srv_api'].start()

            return True

        except ipautil.CalledProcessError as e:
            if e.returncode == 124:
                logger.debug("Process did not complete before timeout")

            return False

    def restore_state(self):

        restored = False

        try:
            restored = self.fstore.restore_file(self.ntp_confile)

        except ValueError:
            logger.debug("Configuration file %s was not restored.", self.ntp_confile)

        if restored:
            ntpmethods.service_command()['srv_api'].restart()

        else:
            ntpmethods.service_command()['srv_api'].stop()
            ntpmethods.service_command()['srv_api'].disable()

        try:
            ntpmethods.restore_forced_service(self.statestore)
        except CalledProcessError as e:
            logger.error("Failed to restore time synchronization service "
                         "%s", e)


class BaseNTPServer(service.Service):
    def __init__(self, service_name):
        super(BaseNTPServer, self).__init__(
            service_name=service_name,
        )


class BaseServerConfig(service.Service):
    def __init__(self, fstore=None, ntp_conf=None,
                 local_srv=None, fudge=None, needopts=None, service_name=None,
                 ntp_servers=None, ntp_pool=None):

        self.ntp_conf = ntp_conf
        self.local_srv = local_srv
        self.fudge = fudge
        self.needopts = needopts
        self.service_name = service_name
        self.ntp_servers = ntp_servers
        self.ntp_pool = ntp_pool

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
