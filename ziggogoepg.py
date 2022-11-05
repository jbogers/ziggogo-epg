#!/usr/bin/env python3
"""
ZiggoGo EPG

Grabber for the EPG hosted by Ziggo on ziggogo.tv
"""
import argparse
import logging
import os.path
import sys

from classes.tvsystemio import ChannelFileIo, TVHeadendIo, TVSystemIoException, XMLTVFileIo
from classes.ziggoepggrabber import GrabException, ZiggoGoEpgGrabber

LOGGING_FORMAT = "%(asctime)s [%(levelname)8s]: %(message)s"


def main():
    """Program main entry point"""
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=LOGGING_FORMAT)
    logging.info("Starting ZiggoGo EPG")

    parser = argparse.ArgumentParser(description="ZiggoGo EPG grabber", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "-s", "--configuration", default="ziggo-nl", type=str, help="configuration to use", metavar="CONFIGURATION"
    )
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
    channel_group = file_arg_group.add_mutually_exclusive_group()
    channel_group.add_argument(
        "--channel-file", default="channels.txt", type=str, help="file containing the channel list", metavar="FILENAME"
    )
    channel_group.add_argument(
        "-c",
        "--channel",
        action="append",
        type=str,
        help="name of channel to grab, can be given multiple times",
        metavar="CHANNEL",
        dest="channels",
    )
    output_file_group = file_arg_group.add_mutually_exclusive_group()
    output_file_group.add_argument(
        "--write-channel-list",
        action="store_true",
        help="if given all known channels will be written to the file given by '--channel-file', overwriting any existing file",
    )
    output_file_group.add_argument("--xmltv-file", default="ziggogo.xml", type=str, help="xmltv output file", metavar="FILENAME")

    tweak_arg_group = parser.add_argument_group("tweaks", description="Finetuning for advanced users")
    tweak_arg_group.add_argument(
        "--timezone", default=None, type=str, help="override timezone to use in the XMLTV file", metavar="TZ"
    )
    tweak_arg_group.add_argument(
        "--database-location", default=".", type=str, help="path where the cache database will be created", metavar="PATH"
    )
    tweak_arg_group.add_argument("--generate-only", action="store_true", help="generate XMLTV from an existing cache database")

    args = parser.parse_args()

    database_file = os.path.normpath(os.path.join(args.database_location, "ziggogoepg_cache.sqlite3"))
    module_location = os.path.dirname(os.path.abspath(__file__))
    configuration_file = os.path.normpath(os.path.join(module_location, f"{args.configuration}.yml"))

    if args.file_mode:
        if args.channels:
            tv_system_io = ChannelFileIo(channels=args.channels, xmltv_filename=args.xmltv_file)
        else:
            tv_system_io = XMLTVFileIo(channel_list_filename=args.channel_file, xmltv_filename=args.xmltv_file)

    else:
        tv_system_io = TVHeadendIo(
            host=args.tvh_host,
            port=args.tvh_port,
            username=args.tvh_username,
            password=args.tvh_password,
            xmltv_socket_path=args.tvh_socket,
        )

    try:
        grabber = ZiggoGoEpgGrabber(
            tv_system_io=tv_system_io,
            scan_days=args.scan_days,
            configuration_file=configuration_file,
            database_file=database_file,
            timezone=args.timezone,
        )
    except GrabException as ex:
        logging.error(str(ex))
        return 1

    if args.write_channel_list:
        logging.info(f"Writing channel list to '{args.channel_file}'.")
        try:
            channels = grabber.get_channel_list()
        except GrabException as ex:
            logging.error(str(ex))
            return 1

        try:
            with open(args.channel_file, "wb") as f:
                for channel in channels:
                    f.write(f"{channel['name']}\n".encode("utf-8"))
        except OSError:
            raise TVSystemIoException(
                f"Error writing channel list to '{args.channel_file}'. Is the path correct and is it writable?"
            )

    else:
        try:
            grabber.grab(generate_only=args.generate_only)
        except (GrabException, TVSystemIoException) as ex:
            logging.error(str(ex))
            return 1

    logging.info("Done!")
    return 0


if __name__ == "__main__":
    """Command line entry point"""
    exit(main())
