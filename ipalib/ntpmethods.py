#
# Copyright (C) 2018  FreeIPA Contributors see COPYING for license
#
from __future__ import absolute_import

import shutil
from pkgutil import find_loader
from ipaplatform import services


def service_command():
    timedata_srv = {
        'openntpd': services.knownservices.ntpd,
        'ntpd': services.knownservices.ntpd,
        'chrony': services.knownservices.chronyd
    }

    return timedata_srv[TIME_SERVICE]


def detect_time_server():
    ts_modules = ['ntpdlib', 'ontpdlib', 'chronylib']
    ts = {
        'ntpdlib': 'ntpd',
        'ontpdlib': 'openntpd',
        'chronylib': 'chrony',
    }
    for srv in ts_modules:
        if find_loader('ipalib.%s' % srv):
            return ts[srv]

    return False


TIME_SERVICE = detect_time_server()


def backup_config(path, fstore=None):
    if fstore:
        fstore.backup_file(path)
    else:
        shutil.copy(path, "%s.ipasave" % path)


def write_config(path, content):
    fd = open(path, "w")
    fd.write(content)
    fd.close()


def select_service():
    srv = TIME_SERVICE
    if TIME_SERVICE == 'openntpd' or 'ntpd':
        srv = 'ntpd'
    return srv


def check_timedate_services():
    for service in services.timedate_services:
        if service == select_service():
            continue
        instance = services.service(service)
        if instance.is_enabled() or instance.is_running():
            raise NTPConflictingService(
                conflicting_service=instance.service_name
            )


def is_run():
    return service_command().is_running


def force_service(statestore):
    for service in services.timedate_services:
        if service == select_service():
            continue
        instance = services.service(service)
        enabled = instance.is_enabled()
        running = instance.is_running()
        if enabled or running:
            statestore.backup_state(instance.service_name, 'enabled', enabled)
            statestore.backup_state(instance.service_name, 'running', running)
            if running:
                instance.stop()
            if enabled:
                instance.disable()


def restore_forced_service(statestore):
    for service in services.timedate_services:
        if service == select_service():
            continue
        if statestore.has_state(service):
            instance = services.service(service)
            enabled = statestore.restore_state(instance.service_name,
                                               'enabled')
            running = statestore.restore_state(instance.service_name,
                                               'running')
            if enabled:
                instance.enable()
            if running:
                instance.start()


class NTPConfigurationError(Exception):
    pass


class NTPConflictingService(NTPConfigurationError):
    def __init__(self, message='', conflicting_service=None):
        super(NTPConflictingService, self).__init__(self, message)
        self.conflicting_service = conflicting_service
