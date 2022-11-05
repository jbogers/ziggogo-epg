# ZiggoGo EPG

This script grabs EPG data from the ZiggoGo TV service and formats it into XMLTV format. This script is designed for use with
TVHeadend, but can also be used in standalone mode.

ZiggoGo EPG optimizes grabbing on TV information by using a cache database (implemented using SQLite). By reusing this cache
between runs, the amount of data downloading is severely reduced. This has 2 main advantages. First of all, grabbing is a lot
faster (except for the initial run, obviously) as a lot less requests to the Ziggo server need to be made. Secondly, because a
lot less request are being made to the Ziggo server, the impact of running ZiggoGo EPG on these servers will be limited.

Even though ZiggoGo EPG is optimized, it is not recommended to run this program more than twice a day. If more frequent XMLTV
generation is desired (for example, for testing purposes), use the `--generate-only` flag. See the [Usage](#usage) section for
more details.

## TVHeadend mode

In this mode, TVHeadend will be asked to provide a list of known TV channels. The script will try to match these up to the
ZiggoGo EPG and only grab data for these channels. Once the EPG data has been grabbed, the resulting XMLTV data is directly
written to TVHeadend without creating an intermediate file.

The TVHeadend mode is the recommended mode for ZiggoGo EPG and is thus the default mode.

## Standalone mode

In this mode, the channel list will be read from an input file (recommended) or can be given per channel on the command line.
The XMLTV data will then be output to the file of choice.

For convenience, ZiggoGo EPG can output all known channels to a file. This file can be edited to the users desire and then used
as the input file.

## Requirements

Python 3.6+ is required to run this script. In addition, some external Pyton packages are used. These are listed in the
`requirements.txt` file. You can easily install these packages using the following command:
```shell
pip install -r requirements.txt
```

## Usage

For a quick overview of all available options, run:
```shell
./ziggogoepg.py --help
```

ZiggoGo EPG supports the following basic options:
- `-h`, `--help`: Opens the program help and exits.
- `-s`, `--configuration`: Select the configuration to use. The default configuration is `ziggo-nl`. Currently supported
  configurations are (see also [Adding configurations](adding-configurations)):
  - `upc-pl`
  - `ziggo-nl`
- `-n`, `--scan-days`: Set the number of days to scan from the ZiggoGo servers. The default of 14 is the current maximum of
  the servers. To reduce grabbing time, memory use and storgae requirements, this value can be lowered.
- `-f`, `--file-mode`: Runs the grabber in file mode instead of the default TVHeadend mode. See the
  [TVHeadend mode](#tvheadend-mode) and [Standalone mode](#standalone-mode) sections for a detailed explanation.

The following options are supported in TVHeadend mode:
- `--tvh-host`: Give the hostname of the TVHeadend server. Defaults to `localhost`, which should be safe as writing the XMLTV file
  can normally only be done on the local machine (unless you are using a networked file system).
- `--tvh-port`: Give the port number of the TVHeadand server. Defaults to `9981`, which should normally work unless you configured
  TVHeadend to run on a different port.
- `--tvh-username`: The username to use for connecting to TVHeadend. This can (and should) be a user with limited access.
- `--tvh-password`: The password to use for connecting to TVHeadend. Note that this password can be seen on the command line.
- `--tvh-socket SOCKET`: The path to xmltv socket of TVHeadend, used to write the XMLTV data. Defaults to
  `/home/hts/.hts/tvheadend/epggrab/xmltv.sock` which should work for any installation that installed TVHeadend under the
  recommended system user. Note that this socket file _only_ exists if the XMLTV grabber was enabled in TVHeadend.

The following options are supported in standalone file mode:
- `--channel-file`: Sets the filename of the file to read (or write, see `--write-channel-list`) the channel list from. This can
  be only a filename or a full path. Defaults to `channels.txt`.
- `-c`, `--channel`: Can be used instead of the `--channel-file` option to give a specific channel to grab on the command line.
  The option can be repeated multiple times to specify multiple channels (but in that case, using the `--channel-file` is
  _highly_ recommended).
- `--write-channel-list`: If given the currently known channels are retrieved from the ZiggoGo servers and are output to the file
- specified by the `--channel-file` option. No EPG data will be grabbed and no XMLTV file will be generated. This is option is
  useful when first starting with the standalone file mode as this gives a known-good channels file to start your configuration
  with. It is recommended to first edit this file, removing any unwanted channels, before starting normal use of the
  standalne file mode. **Warning**: Using this option will overwrite any existing file at the location of `--channel-file`!

The following options are tweaks that can be used by advanced users:
- `--timezone`: All start and stop (end) times in the XMLTV file have a timezone associated with them. By default
  the timezone from the confifuration file is used as it is most appropriate for your EPG. And your TV software should be
  able to handle this timezone without any issue. However, if you TV software has issues, you can try other timezones. You can
  choose most of the timezones listed on https://en.wikipedia.org/wiki/List_of_tz_database_time_zones, with 'UTC' being your best
  bet in case of issues. Note that timezone assignment and translation is done by the `pytz` library, so if this library is kept
  up to date you should experience no timezone issues.
- `--database-location`: By default the `ziggoepg_cache.sqlite` file is stored in the working directory of the script. Should you
  desire a different location (for example, a file system that is better suited to handle a database file), an alternative path
  (but not filename) can be specified here.
- `--generate-only`: Great for testing the export of the XMLTV data. No contact is made with the ZiggoGo servers, the XMLTV
  generation is done fully from the existing `ziggoepg_cache.sqlite` file. Any useful application of this mode requires ZiggoGo
  EPG to have run in a normal mode at least once before. Note that this option is ignored if the `--write-channel-list` option
  is used. Note that the `--channel-file`, `-c` or changing available channels in TVHeadand has no effect on the output of this
  option (these options control updating of the `ziggoepg_cache.sqlite` file only).

## Adding configurations

Configuration files are stored with the ZiggoGo EPG program in `.yml` (YAML) files. To create a new configuration it is easiest
to copy an existing one and name it accordingly for your region. In the configuration file, you can adjust the URL's used to
grab the EPG data from and set an appropriate timezone for the resulting XMLTV file. Note that this grabber only works with
systems from Ziggo/UPC/Liberty Global and you will have to figure out the URL's yourself by observing the network traffic of
the online viewing application from your local provider.

The following configuration options are available:
- `urls`
  - `epg_channel_list`: The URL where the grabber can get the currently supported channel list from the online viewer. This gives
    the grabber the information it needs to map TV channel names to the internal ID's used by the EPG service.
  - `epg_segment`: The URL where the grabber can get the program overview segments. Typically, these are 6-hour segments that
    contain an overview of all programs broadcast during that period. The URL must have exactly one `{}` entry, which is to be
    placed in the location of the URL where the segment id is normally placed. A segment id looks like a datetime without any
    spacing or symbols (eg. 2022-03-11, 00:00:00 becomes `20220311000000`, which is automatically generated by the grabber in
    place of the `{}` entry).
  - `epg_detail`: The URL where the grabber can get the program details from each individual program. The URL must have exactly
    one `{}` entry, which is to be placed in the location of the URL where the program id is normally placed. A program id is a
    long string that is associated with the program. This value can be seen both in the segment data and from observing the URL
    called by the online viewing application from your local provider.
- `timezone`: The timezone that is used for creating program entries in the XMLTV file. This timezone must be supported by
  `pytz`. See the explanation of the `--timezone` option for what is allowed here.

After creating the configuration, place it in the ziggogo-epg application location and call `ziggogoepg.py` with the
`-s`/`--configuration` option, where the value is the name ofthe file without the `.yml` extension (for example, to use
`upc-pl.yml`, you would call `ziggogoepg.py` with the option `-s upc-pl`).

## Acknowledgments

Inspiration for the script has been taken from https://github.com/beralt/horepg. While all code is new, some operational ideas
(like automatic channel matching with TvHeaded) came from this project.

Thank you [Beralt](https://github.com/beralt) for your hard work on [horepg](https://github.com/beralt/horepg)!

Also thanks to:
- [ldymek](https://github.com/ldymek) for providing the configuration information for `upc-pl`.

## TODO's

- Add a setup.cfg/setup.py file to make the program installable as a Python module for the people who perfer that run mode.
- Implement an optional category translation similar to 'https://github.com/beralt/horepg/blob/master/horepg/xmltvdoc.py' in 
  XMLTVWriter to have proper category mapping in TVHeadend.
  - Translated categories should be additionally added as the original data may be applicable for other applications.
