# Winapp2.ini

This repository contains the Winapp2.ini file that can be used with BleachBit to add additional functionality.

This repository previously was used to track a (partial) history of the Winapp2.ini file that was maintained at www.winapp2.com plus some of the removed entries, which were added back in for use with [BleachBit](https://www.bleachbit.org). Now the development of the upstream file moved to [its own GitHub repository](https://github.com/MoscaDotTo/Winapp2) (called "upstream" here), so new history is tracked there.

## Files

* [Winapp2-BleachBit.ini](https://github.com/bleachbit/winapp2.ini/blob/master/Winapp2-BleachBit.ini): the file for use with BleachBit - ***this is likely what you want***
* Winapp2.ini: the unmodified file from upstream with entries removed for CCleaner added back in
* check_ini.py: Sanity checks for Winapp2.ini
* merge-commit.sh: Processing and sanity checks for Winapp2.ini
* profile.sh: Generate statistics on FileKey#, DetectKey#, and Environment Variables

## Reporting bugs
For bugs in the unmodified Winapp2.ini file or to report a change that belongs upstream (which benefits BleachBit, CCleaner, System Ninja, and Avira System Speedup), please see the [Winapp2 GitHub page](https://github.com/MoscaDotTo/Winapp2/).

For issues with the Winapp2.ini as it relates specifically to BleachBit, please file a [bug report in the BleachBit winapp2.ini repository](https://github.com/bleachbit/winapp2.ini/issues). If the issue is with the BleachBit application (for example, how it interprets the Winapp2.ini), please file the issue in the [BleachBit application repository](https://github.com/bleachbit/bleachbit/issues).

## License

The Winapp2.ini file does not have an explicit license. The original software in this repository (Bash and Python) are licensed under the [GNU GPL version 3 or later](https://www.gnu.org/copyleft/gpl.html).
