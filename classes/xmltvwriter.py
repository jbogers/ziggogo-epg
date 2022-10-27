"""
ZiggoGo EPG

XML TV structure writer
"""

import json
import logging
import sqlite3

from lxml import etree


class XMLTVWriter:
    """Write XMLTV data from database"""

    def __init__(self, database_connection: sqlite3.Connection):
        """
        Initialize XMLTVWriter.

        :param database_connection: An opened SQLite database connection to the EPG data
        """
        self._db = database_connection
        self._dbcur = self._db.cursor()

        # NL is hardcoded as it is the only language ZiggoGo provides.
        self._lang = "nl"

    def generate_xmltv(self) -> bytes:
        """
        Generate the XMLTV file from the database.
        :return: The XMLTV data as a string
        """

        logging.info("Generating XMLTV data...")

        xmltv = etree.Element(
            "tv",
            attrib={
                "source-info-url": "https://www.ziggogo.tv",
                "source-info-name": "ZiggoGo",
                "generator-info-name": "ZiggoGo EPG",
                "generator-info-url": "https://github.com/jbogers/ziggogo-epg",
            },
        )

        self._add_channels(xmltv=xmltv)
        self._add_programmes(xmltv=xmltv)

        return etree.tostring(xmltv, pretty_print=True)

    def _add_channels(self, xmltv: etree.Element):
        """Add the channels to the XMLTV element"""

        self._dbcur.execute("SELECT id, name, logo FROM channels")

        for row in self._dbcur:
            channel = etree.SubElement(xmltv, "channel", attrib={"id": row["id"].replace("_", ".")})
            etree.SubElement(channel, "display-name", attrib={"lang": self._lang}).text = row["name"]

            if row["logo"]:
                etree.SubElement(channel, "icon", attrib={"src": row["logo"]})

    def _add_programmes(self, xmltv: etree.Element):
        """Add the programmes to XMLTV element"""

        self._dbcur.execute(
            "SELECT channelid, title, starttime, endtime, pd.details AS details FROM programmes p "
            "LEFT JOIN programmedetails pd ON pd.id = p.id"
        )

        for row in self._dbcur:
            programme = etree.SubElement(
                xmltv,
                "programme",
                attrib={"start": row["starttime"], "stop": row["endtime"], "channel": row["channelid"].replace("_", ".")},
            )
            etree.SubElement(programme, "title", attrib={"lang": self._lang}).text = row["title"]

            if row["details"] is not None:
                details = json.loads(row["details"])

                if "sub-title" in details:
                    etree.SubElement(programme, "sub-title", attrib={"lang": self._lang}).text = details["sub-title"]

                if "desc" in details:
                    etree.SubElement(programme, "desc", attrib={"lang": self._lang}).text = details["desc"]

                if "credits" in details:
                    credits = etree.SubElement(programme, "credits")
                    if "directors" in details["credits"]:
                        for director in details["credits"]["directors"]:
                            etree.SubElement(credits, "director").text = director
                    if "actors" in details["credits"]:
                        for actor in details["credits"]["actors"]:
                            etree.SubElement(credits, "actor").text = actor
                    if "producers" in details["credits"]:
                        for producers in details["credits"]["producers"]:
                            etree.SubElement(credits, "producer").text = producers

                if "date" in details:
                    etree.SubElement(programme, "date").text = details["date"]

                if "categories" in details:
                    # TODO: Offer translation option that adds DVB-EPG compatible types
                    for category in details["categories"]:
                        etree.SubElement(programme, "category", attrib={"lang": self._lang}).text = category

                if "country" in details:
                    etree.SubElement(programme, "country").text = details["country"]

                if "episode" in details:
                    season = ""
                    ziggo_internal_id = False
                    try:
                        season = int(details["episode"]["season"]) - 1
                        if season >= 99999:
                            # Fake season number used in ZiggoGo that should never be displayed
                            ziggo_internal_id = True
                    except (KeyError, ValueError):
                        # No season value or not an integer
                        pass
                    episode = ""
                    try:
                        episode = int(details["episode"]["episode"]) - 1
                        if episode >= 9999999:
                            # Fake episode number used in ZiggoGo that should never be displayed
                            ziggo_internal_id = True
                    except (KeyError, ValueError):
                        # No season value or not an integer
                        pass
                    if not ziggo_internal_id and (season != "" or episode != ""):
                        etree.SubElement(programme, "episode-num", attrib={"system": "xmltv_ns"}).text = f"{season}.{episode}."

                if "rating" in details:
                    rating = etree.SubElement(programme, "rating", attrib={"system": "Kijkwijzer"})
                    etree.SubElement(rating, "value").text = details["rating"]

    def __del__(self):
        """Cleanup"""
        self._dbcur.close()
