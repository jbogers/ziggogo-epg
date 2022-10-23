"""
ZiggoGo EPG

Main grabber class for the ZiggoGo EPG.
"""
import datetime
import json
import pytz
import requests
import sqlite3
import sys
import time

from typing import Iterable, List

from classes.tvsystemio import TVSystemIo, TVSystemIoException
from classes.xmltvwriter import XMLTVWriter


class GrabException(Exception):
    """Failure grabbing EPG"""


class ChannelMatcher:
    """Matches a given channel with a known channel list"""

    def __init__(self, channels: Iterable[str]):
        """Initialize with known channel list"""
        # Store as lowercase, without whitespace and without 'HD' tag
        self._known_channels = {}
        for channel in channels:
            channel_id = channel.lower().strip()
            if channel_id.endswith(" hd"):
                channel_id = channel_id[:-3].strip()
            self._known_channels[channel_id] = channel

    def is_known(self, channel: str) -> bool:
        """Match channel with list of known channels. Returns True if channel is found, False if it is not."""
        channel = channel.lower().strip()
        if channel.endswith(" hd"):
            channel = channel[:-3].strip()

        return channel in self._known_channels


class ZiggoGoEpgGrabber:
    """Grabber for the EPG hosted by Ziggo on ziggogo.tv"""

    def __init__(
        self, tv_system_io: TVSystemIo, scan_days=14, timezone="Europe/Amsterdam", database_file="ziggogoepg_cache.sqlite3"
    ):
        """
        Initialize ZiggoGoEpgGrabber

        :param tv_system_io: Instance of a TVSystemIo object to be used for getting desired channels and writing out the XMLTV
        :param scan_days: Number of days to scan for
        :param timezone: Timezone string supported by pytz
        :param database_file: The name and location of teh database file to use
        """
        self._tv_system_io = tv_system_io

        # Set up URL's statically
        self._epg_channel_list_url = (
            "https://prod.spark.ziggogo.tv/eng/web/linear-service/v2/channels?cityId=65535&language=nl&productClass=Orion-DASH"
        )
        self._epg_segment_url = "https://static.spark.ziggogo.tv/eng/web/epg-service-lite/nl/nl/events/segments/{}"
        self._epg_detail_url = (
            "https://prod.spark.ziggogo.tv/eng/web/linear-service/v2/replayEvent/{}?returnLinearContent=true&language=nl"
        )

        self._grab_start_time = None

        # Set up options statically (for now)
        self._scan_days = scan_days
        self._timezone = pytz.timezone(timezone)

        # Create or open database
        self._db = sqlite3.connect(database_file)
        self._db.row_factory = sqlite3.Row
        self._dbcur = self._db.cursor()
        self._dbcur.arraysize = 1024  # Optimize 'fetchall' operations

        # Create database tables if they do not exist yet
        self._dbcur.execute(
            """
            CREATE TABLE IF NOT EXISTS channels (
                id TEXT PRIMARY KEY,
                last_update INTEGER NOT NULL,
                name TEXT NOT NULL,
                logo TEXT
            )
        """
        )
        self._dbcur.execute(
            """
            CREATE TABLE IF NOT EXISTS programmes (
                id TEXT PRIMARY KEY,
                channelid TEXT NOT NULL,
                last_update INTEGER NOT NULL,
                title TEXT NOT NULL,
                starttime INTEGER NOT NULL,
                endtime INTEGER NOT NULL
            )
        """
        )
        self._dbcur.execute(
            """
            CREATE TABLE IF NOT EXISTS programmedetails (
                id TEXT PRIMARY KEY,
                details TEXT NOT NULL
            )
        """
        )

    def __del__(self):
        """Cleanup"""
        self._dbcur.close()
        self._db.close()

    def grab(self, generate_only=False):
        """Perform EPG grab. Raises GrabException on error."""

        self._grab_start_time = int(time.time())

        if not generate_only:
            channel_ids = self._grab_channels()
            self._grab_programmes(channel_ids=channel_ids)
            self._grab_programmedetails()

            print("Cleaning up database...")
            self._dbcur.execute("VACUUM")
        else:
            print("Generate only: skip grabbing new EPG data")

        xmltv_writer = XMLTVWriter(database_connection=self._db)
        xmltv = xmltv_writer.generate_xmltv()

        self._tv_system_io.write_xmltv(data=xmltv)

    def get_channel_list(self) -> List:
        """
        Get the channel list from the EPG server

        :return: A list of channels as dictionaries, containing the keys: id, name, logo
        """
        channel_list = []
        with requests.get(self._epg_channel_list_url) as r:
            try:
                channeldata = r.json()
            except requests.exceptions.JSONDecodeError:
                raise GrabException(
                    f"Failure decoding server response for channel data. The HTTP code was {r.status_code}.\n"
                    f"The response text was:\n{r.text}"
                )

            for channel in channeldata:
                try:
                    logo = None
                    if "logo" in channel and "focused" in channel["logo"]:
                        logo = channel["logo"]["focused"]

                    channel_list.append(
                        {
                            "id": channel["id"],
                            "name": channel["name"],
                            "logo": logo,
                        }
                    )
                except KeyError:
                    # Required info not present for channel, skip
                    continue

        return channel_list

    def _grab_channels(self) -> List[str]:
        """
        Get updated channel list and check if they are requested

        :return: A list with all found channel id's
        """
        channel_matcher = ChannelMatcher(channels=self._tv_system_io.get_channel_list())

        print("Getting known channels from EPG...")
        channel_list = self.get_channel_list()

        channelupdate = []
        for channel in channel_list:
            if not channel_matcher.is_known(channel["name"]):
                continue

            channel["last_update"] = self._grab_start_time
            channelupdate.append(channel)

        # Add filtered channels to database
        self._dbcur.executemany(
            "INSERT OR REPLACE INTO channels (id, last_update, name, logo) VALUES (:id, :last_update, :name, :logo)",
            channelupdate,
        )

        # Purge unwanted channels
        print("Cleaning up channels table...")
        self._dbcur.execute("DELETE FROM channels WHERE last_update != ?", (self._grab_start_time,))
        self._db.commit()

        return [channel["id"] for channel in channelupdate]

    def _grab_programmes(self, channel_ids):
        """Grab segment information and extract programmes for the given channels only"""
        print("Getting guide overview data...")

        # Determine start point using UTC time as segment codes are in UTC
        grab_start = datetime.datetime.utcfromtimestamp(self._grab_start_time)
        segment_datetime = datetime.datetime(year=grab_start.year, month=grab_start.month, day=grab_start.day)
        end_datetime = segment_datetime + datetime.timedelta(days=self._scan_days)

        session = requests.Session()
        while segment_datetime < end_datetime:
            segment_code = segment_datetime.strftime("%Y%m%d%H%M%S")
            print(f"  Segment: {segment_code}")

            # Expected to fail at some point
            with session.get(self._epg_segment_url.format(segment_code)) as r:
                if r.status_code == 404:
                    # No more segment data, stop grabbing
                    print(f"No more EPG data found at {segment_datetime}, stopping scan.")
                    break

                try:
                    segmentdata = r.json()
                except requests.exceptions.JSONDecodeError:
                    raise GrabException(
                        f"Failure decoding server response for segment data. The HTTP code was {r.status_code}.\n"
                        f"The response text was:\n{r.text}"
                    )

            if "duration" not in segmentdata or not isinstance(segmentdata["duration"], int) or segmentdata["duration"] <= 0:
                print(f"WARNING: Segment {segment_code} duration is not properly encoded, using 6 hour interval", file=sys.stderr)
                segment_datetime += datetime.timedelta(hours=6)
            else:
                segment_datetime += datetime.timedelta(seconds=segmentdata["duration"])

            if "entries" not in segmentdata:
                print(f"WARNING: Segment {segment_code} is missing entries. Skipping.")
                continue

            for entry in segmentdata["entries"]:
                if "events" not in entry:
                    # Channel has no programmes, skip
                    continue
                if entry["channelId"] not in channel_ids:
                    # Channel we are not interested in, skip
                    continue

                programmeupdate = []
                for event in entry["events"]:

                    programmeupdate.append(
                        {
                            "id": event["id"],
                            "channelid": entry["channelId"],
                            "last_update": self._grab_start_time,
                            "title": event["title"],
                            "starttime": datetime.datetime.fromtimestamp(event["startTime"], self._timezone).strftime(
                                "%Y%m%d%H%M%S %z"
                            ),
                            "endtime": datetime.datetime.fromtimestamp(event["endTime"], self._timezone).strftime(
                                "%Y%m%d%H%M%S %z"
                            ),
                        }
                    )

                self._dbcur.executemany(
                    "INSERT OR REPLACE INTO programmes (id, channelid, last_update, title, starttime, endtime)"
                    "VALUES (:id, :channelid, :last_update, :title, :starttime, :endtime)",
                    programmeupdate,
                )

            # Commit data per segment to be more robust against script failure
            self._db.commit()

        # Purge old data
        print("Cleaning up programme table...")
        self._dbcur.execute("DELETE FROM programmes WHERE last_update != ?", (self._grab_start_time,))
        self._db.commit()

    def _grab_programmedetails(self):
        """Grab missing programme details from all programmes in the programmes table"""
        # First purge unused programme details
        print("Cleaning up programme details table...")
        self._dbcur.execute("DELETE FROM programmedetails WHERE id NOT IN (SELECT id FROM programmes)")
        self._db.commit()

        # Grab missing details (using separate cursor)
        print("Getting missing programme details...")
        self._dbcur.execute("SELECT p.id FROM programmes p LEFT JOIN programmedetails pd ON pd.id = p.id WHERE pd.id IS NULL")
        missing_programmes_rows = self._dbcur.fetchall()

        programmecounter = 0
        totalcount = len(missing_programmes_rows)
        detailsupdate = []
        session = requests.Session()

        for row in missing_programmes_rows:
            programmecounter += 1
            id = row[0]

            with session.get(self._epg_detail_url.format(id)) as r:
                if r.status_code != 200:
                    # Programme not found, skip
                    continue

                try:
                    programmedata = r.json()
                except requests.exceptions.JSONDecodeError:
                    print(f"WARNING: Programme data for '{id}' could not be read, skipping.", file=sys.stderr)
                    continue

                # Add title first, as it should always exist
                try:
                    details = {"title": programmedata["title"]}
                except KeyError:
                    print(f"WARNING: Programme data for '{id}' is missing title data, skipping.", file=sys.stderr)
                    continue

                # Add optional data, structuring it mostly as it will be in the XMLTV
                if "episodeName" in programmedata:
                    details["sub-title"] = programmedata["episodeName"]

                if "longDescription" in programmedata:
                    details["desc"] = programmedata["longDescription"]
                elif "shortDescription" in programmedata:
                    details["desc"] = programmedata["shortDescription"]

                credits = {}
                if "actors" in programmedata:
                    credits["actors"] = programmedata["actors"]
                if "directors" in programmedata:
                    credits["directors"] = programmedata["directors"]
                if "producers" in programmedata:
                    credits["producers"] = programmedata["producers"]
                if credits:
                    details["credits"] = credits

                if "productionDate" in programmedata:
                    details["date"] = programmedata["productionDate"]

                if "genres" in programmedata:
                    details["categories"] = programmedata["genres"]

                if "countryOfOrigin" in programmedata:
                    details["country"] = programmedata["countryOfOrigin"]

                episode = {}
                if "seasonNumber" in programmedata:
                    episode["season"] = programmedata["seasonNumber"]
                if "episodeNumber" in programmedata:
                    episode["episode"] = programmedata["episodeNumber"]
                if episode:
                    details["episode"] = episode

                if "minimumAge" in programmedata:
                    details["rating"] = programmedata["minimumAge"]

                # Store details as JSON data
                detailsupdate.append({"id": id, "details": json.dumps(details)})

            # Dump data to table per 100 programmes
            if len(detailsupdate) >= 100:
                self._dbcur.executemany("INSERT INTO programmedetails (id, details) VALUES (:id, :details)", detailsupdate)
                self._db.commit()
                detailsupdate = []
                print(f"   {programmecounter}/{totalcount} programmes fetched...")

        if detailsupdate:
            self._dbcur.executemany("INSERT INTO programmedetails (id, details) VALUES (:id, :details)", detailsupdate)
            self._db.commit()
            print(f"   {programmecounter}/{totalcount} programmes fetched...")
        elif programmecounter == 0:
            print(f"   No update of programme details needed...")
