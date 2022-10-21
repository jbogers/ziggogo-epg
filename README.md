# ZiggoGo EPG

This script grabs EPG data from the ZiggoGo TV service and formats it into XMLTV format.

This script is optimized for use with TvHeadend, but can also be used in standalone mode.

## TvHeadend mode

Documentation to be added. In this mode, TvHeadend will be asked to provide a list of known TV
channels. The script will then try match these up to the ZiggoGo EPG and only grab data for these
channels.

The XMLTV file is automatically send back to TvHeadend.

## Standalone mode

Documentation to be added. In this mode, the configuration file is used to indicate what TV channels
the EPG should be grabbed for. The XMLTV file will be output to disk.

## Acknowledgments

Inspiration for the script has been taken from https://github.com/beralt/horepg. While all code is
new, some operational ideas (like automatic channel matching with TvHeaded) came from this project.

Thank you [Beralt](https://github.com/beralt) for your hard work on
[horepg](https://github.com/beralt/horepg)!
