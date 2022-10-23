"""
ZiggoGo EPG

TVSystemIo classes that handle interaction with TvHeadend or simple disk files.
"""

import requests
import socket

from requests.auth import HTTPBasicAuth, HTTPDigestAuth
from typing import List


class TVSystemIoException(Exception):
    """Failure interacting with TV system"""


class TVSystemIo:
    """Base class used for getting the channel list and writing out the EPG"""

    def get_channel_list(self) -> List[str]:
        """Get the list of channels to grab the EPG for"""
        raise NotImplementedError()

    def write_xmltv(self, data: bytes):
        """Write the XMLTV EPG to storage"""
        raise NotImplementedError()


class TvHeadendIo(TVSystemIo):
    """Class used to interact with TVHeadend for the EPG"""

    def __init__(
        self,
        host="localhost",
        port=9981,
        username="",
        password="",
        xmltv_socket_path="/home/hts/.hts/tvheadend/epggrab/xmltv.sock",
    ):
        """Initialize the TvHeadendIo class"""
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._xmltv_socket_path = xmltv_socket_path

    def get_channel_list(self) -> List[str]:
        """Get the list of channels from TVHeadend"""
        print("Requesting known channel list from TVHeadend...")
        try:
            r = requests.get(
                f"http://{self._host}:{self._port}/api/channel/list",
                auth=HTTPBasicAuth(username=self._username, password=self._password),
            )
        except requests.ConnectionError:
            raise TVSystemIoException(f"Could not connect to TVHeadend on http://{self._host}:{self._port}.")

        if r.status_code == 401:
            # Also try Digest authentication
            r.close()
            r = requests.get(
                f"http://{self._host}:{self._port}/api/channel/list",
                auth=HTTPDigestAuth(username=self._username, password=self._password),
            )
        if r.status_code != 200:
            raise TVSystemIoException(f"Error getting channel list from TVHeadend. The status code was: {r.status_code}")

        try:
            channeldata = r.json()
        except requests.exceptions.JSONDecodeError:
            raise TVSystemIoException(f"Error getting channel list from TVHeadend. The list was not valid JSON data.")

        try:
            channellist = [channel["val"] for channel in channeldata["entries"]]
        except KeyError:
            raise TVSystemIoException(f"Error getting channel list from TVHeadend. The list was not structured properly.")

        return channellist

    def write_xmltv(self, data: bytes):
        """Write the XMLTV EPG to TVHeadend directly"""
        print("Writing XMLTV directly to TVHeadend...")
        try:
            sock = socket.socket(socket.AF_UNIX)
            try:
                sock.connect(self._xmltv_socket_path)
                sock.sendall(data)
            finally:
                sock.close()

        except OSError:
            raise TVSystemIoException(
                f"Error writing XMLTV to '{self._xmltv_socket_path}'. Is the path correct and is TVHeadend running?"
            )


# TODO: Add direct file IO that writes to disk
