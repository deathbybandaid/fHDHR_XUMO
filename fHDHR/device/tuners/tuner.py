import multiprocessing
import threading
import datetime

from fHDHR.exceptions import TunerError
from fHDHR.tools import humanized_time

from .stream import Stream


class Tuner():
    def __init__(self, fhdhr, inum, epg):
        self.fhdhr = fhdhr

        self.number = inum
        self.epg = epg

        self.tuner_lock = threading.Lock()
        self.set_off_status()

        if fhdhr.config.dict["fhdhr"]["address"] == "0.0.0.0":
            self.location = ('http://127.0.0.1:%s' % str(fhdhr.config.dict["fhdhr"]["port"]))
        else:
            self.location = ('http://%s:%s' % (fhdhr.config.dict["fhdhr"]["address"], str(fhdhr.config.dict["fhdhr"]["port"])))

        self.chanscan_url = "%s/api/channels?method=scan" % (self.location)
        self.close_url = "%s/api/tuners?method=close&tuner=%s" % (self.location, str(self.number))

    def channel_scan(self):
        if self.tuner_lock.locked():
            self.fhdhr.logger.error("Tuner #%s is not available." % str(self.number))
            raise TunerError("804 - Tuner In Use")

        if self.status["status"] == "Scanning":
            self.fhdhr.logger.info("Channel Scan Already In Progress!")
        else:

            self.tuner_lock.acquire()
            self.status["status"] = "Scanning"
            self.fhdhr.logger.info("Tuner #%s Performing Channel Scan." % str(self.number))

            if self.fhdhr.config.dict["main"]["thread_method"] in ["multiprocessing"]:
                chanscan = multiprocessing.Process(target=self.runscan)
            elif self.fhdhr.config.dict["main"]["thread_method"] in ["threading"]:
                chanscan = threading.Thread(target=self.runscan)
            if self.fhdhr.config.dict["main"]["thread_method"] in ["multiprocessing", "threading"]:
                chanscan.start()

    def runscan(self):
        self.fhdhr.web.session.get(self.chanscan_url)
        self.fhdhr.logger.info("Requested Channel Scan Complete.")
        self.fhdhr.web.session.get(self.close_url)

    def add_downloaded_size(self, bytes_count):
        if "downloaded" in list(self.status.keys()):
            self.status["downloaded"] += bytes_count

    def grab(self, channel_number):
        if self.tuner_lock.locked():
            self.fhdhr.logger.error("Tuner #" + str(self.number) + " is not available.")
            raise TunerError("804 - Tuner In Use")
        self.tuner_lock.acquire()
        self.status["status"] = "Acquired"
        self.status["channel"] = channel_number
        self.fhdhr.logger.info("Tuner #%s Acquired." % str(self.number))

    def close(self):
        self.set_off_status()
        if self.tuner_lock.locked():
            print("is locked, releasing")
            self.tuner_lock.release()
        self.fhdhr.logger.info("Tuner #" + str(self.number) + " Released.")

    def get_status(self):
        current_status = self.status.copy()
        current_status["locked"] = self.tuner_lock.locked()
        if current_status["status"] == "Active":
            current_status["Play Time"] = str(
                humanized_time(
                    int((datetime.datetime.utcnow() - current_status["time_start"]).total_seconds())))
            current_status["time_start"] = str(current_status["time_start"])
            current_status["epg"] = self.epg.whats_on_now(current_status["channel"])
        return current_status

    def set_off_status(self):
        self.status = {"status": "Inactive"}

    def get_stream(self, stream_args, tuner):
        stream = Stream(self.fhdhr, stream_args, tuner)
        return stream.get()

    def set_status(self, stream_args):
        if self.status["status"] != "Active":
            self.status = {
                            "status": "Active",
                            "clients": [],
                            "clients_id": [],
                            "method": stream_args["method"],
                            "accessed": [stream_args["accessed"]],
                            "channel": stream_args["channel"],
                            "proxied_url": stream_args["channelUri"],
                            "time_start": datetime.datetime.utcnow(),
                            "downloaded": 0
                            }
        if stream_args["client"] not in self.status["clients"]:
            self.status["clients"].append(stream_args["client"])
        if stream_args["client_id"] not in self.status["clients_id"]:
            self.status["clients_id"].append(stream_args["client_id"])
