#!/usr/bin/env python3
"""
ZiggoGo EPG

Grabber for the EPG hosted by Ziggo on ziggogo.tv
"""
import argparse
import os.path
import sys

from classes.tvsystemio import TvHeadendIo, TVSystemIoException
from classes.ziggoepggrabber import GrabException, ZiggoGoEpgGrabber


def main():
    """Program main entry point"""

    parser = argparse.ArgumentParser(description="ZiggoGo EPG grabber", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-n", "--scan-days", default=14, type=int, help="number of days to grab", metavar="DAYS")
    parser.add_argument("-f", "--file-mode", action="store_true", help="use file mode instead of TVHeadend mode")

    tvh_arg_group = parser.add_argument_group("tvheadend mode", description="Arguments used in TVHeadend mode only (the default)")
    tvh_arg_group.add_argument(
        "--tvh-host",
        default="localhost",
        type=str,
        help="hostname of TVHeadend, used for getting the channel list",
        metavar="HOSTNAME",
    )
    tvh_arg_group.add_argument(
        "--tvh-port", default=9981, type=int, help="portnumber of TVHeadend, used for getting the channel list", metavar="PORT_NR"
    )
    tvh_arg_group.add_argument(
        "--tvh-username", default="", type=str, help="username of TVHeadend, used for getting the channel list", metavar="USER"
    )
    tvh_arg_group.add_argument(
        "--tvh-password", default="", type=str, help="password of TVHeadend, used for getting the channel list", metavar="PASS"
    )
    tvh_arg_group.add_argument(
        "--tvh-socket",
        default="/home/hts/.hts/tvheadend/epggrab/xmltv.sock",
        type=str,
        help="path to xmltv socket of TVHeadend, used to write the XMLTV data to",
        metavar="SOCKET",
    )

    file_arg_group = parser.add_argument_group(
        "file mode", description="Arguments used in file mode only (only used if -f/--file-mode has been given)"
    )
    # TODO: Implement file mode

    tweak_arg_group = parser.add_argument_group("tweaks", description="Finetuning for advanced users")
    tweak_arg_group.add_argument(
        "--timezone", default="Europe/Amsterdam", type=str, help="timezone to use in the XMLTV file", metavar="TZ"
    )
    tweak_arg_group.add_argument(
        "--database-location", default=".", type=str, help="path where the cache database will be created", metavar="PATH"
    )
    parser.add_argument("--generate-only", action="store_true", help="generate XMLTV from an existing cache database")

    args = parser.parse_args()

    database_file = os.path.normpath(os.path.join(args.database_location, "ziggogoepg_cache.sqlite3"))

    if args.file_mode:
        print("File mode is not implemented yet", file=sys.stderr)
        tv_system_io = None
        exit(1)
    else:
        tv_system_io = TvHeadendIo(
            host=args.tvh_host,
            port=args.tvh_port,
            username=args.tvh_username,
            password=args.tvh_password,
            xmltv_socket_path=args.tvh_socket,
        )

    grabber = ZiggoGoEpgGrabber(
        tv_system_io=tv_system_io, scan_days=args.scan_days, timezone=args.timezone, database_file=database_file
    )

    try:
        grabber.grab(generate_only=args.generate_only)
    except (GrabException, TVSystemIoException) as ex:
        print(ex, file=sys.stderr)


if __name__ == "__main__":
    """Command line entry point"""
    main()
