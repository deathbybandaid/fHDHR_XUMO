# coding=utf-8

from .originwrapper import OriginServiceWrapper
from .device import fHDHR_Device

import fHDHR.tools

fHDHR_VERSION = "v0.4.5-beta"


class fHDHR_INT_OBJ():

    def __init__(self, settings, logger, db):
        self.version = fHDHR_VERSION
        self.config = settings
        self.logger = logger
        self.db = db

        self.web = fHDHR.tools.WebReq()


class fHDHR_OBJ():

    def __init__(self, settings, logger, db, alternative_epg, origin):
        self.fhdhr = fHDHR_INT_OBJ(settings, logger, db)

        self.originwrapper = OriginServiceWrapper(self.fhdhr, origin)

        self.device = fHDHR_Device(self.fhdhr, self.originwrapper, alternative_epg)

    def __getattr__(self, name):
        ''' will only get called for undefined attributes '''
        if hasattr(self.fhdhr, name):
            return eval("self.fhdhr." + name)