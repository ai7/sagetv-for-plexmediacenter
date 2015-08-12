# sagetv-for-plexmediacenter

SageTV Plug-in for PLEX Media Server

## Overview

This is a complete rewrite and continuation of the
[sagetv-for-plexmediacenter](http://code.google.com/p/sagetv-for-plexmediacenter/)
project hosted on google code.

The code has gotten some much needed love. Performance and stability
has been improved. Some long standing issues have been addressed. The
updated code base should be easier to follow and maintain. I hope this
will allow the project to be continuously improved and refined.

## Download

You can download sagetv-for-plexmediacenter from the
[release](https://github.com/ai7/sagetv-for-plexmediacenter/releases)
page.

The `sagetv-for-plexmediacenter-v*-*.zip` file contains the following directories:

```
+--install
|  \--win32
+--plex
|  +--Plug-ins
|  |  \--BMTAgentTVShows.bundle
|  |     \--Contents
|  |        +--Code
|  |        \--Resources
|  +--Scanners
|  |  +--Movies
|  |  |  \--sageplex
|  |  \--Series
|  |     \--sageplex
|  \--synctool
|     +--python
|     |  \--sageplex
|     \--win32
\--sagetv
   \--sagex
      \--services
```

* **`install`** folder contains Installer for Windows/MacOS/Linux.
* **`plex`** folder contains files for PLEX Media Server.
* **`sagetv`** folder contains files for SageTV.

## Installation

To install sagetv-for-plexmediacenter, extract the zip file and run
the appropriate installer for your platform. The installer will ask
some questions and guide you through the installation process.

The installer can also be used to remove sagetv-for-plexmediacenter
from your system. For more details, see install.txt.

### Windows

```
install\win32\sageplex_install.exe -i
```

### MacOS

```
python install/sageplex_install.py -i
```

### Linux

On Linux, the installer should be invoked as the **plex** user. This
can be done as follow:

```
sudo -u plex python install/sageplex_install.py -i
```

### Manual Install

Follow the instructions below if you wish to perform a manual install.
For MacOS/Linux, simply substitute the appropriate destination
location.

This assumes you are somewhat familiar with this plugin, SageTV, and
PLEX Media Server. If not, please take a look at this [Install
Wiki](http://code.google.com/p/sagetv-for-plexmediacenter/wiki/InstallingAndUsing)
for some background information and requirements.

1. Unzip `sagetv-for-plexmediacenter-v*-*.zip` to a temporary location.
2. Stop SageTV and PLEX Media Server.
2. Copy content of `sagetv` subfolder to the SageTV program folder (where SageTV.exe is).
  * `sagetv\sagex\services\plex.js` -> `c:\program files (x86)\sagetv\sagetv\sagex\services`
3. Copy content of `plex\Scanners` to `%LOCALAPPDATA%\Plex Media Server\Scanners`
  * `plex\Scanners\Movies` -> `%LOCALAPPDATA%\Plex Media Server\Scanners\Movies`
  * `plex\Scanners\Series` -> `%LOCALAPPDATA%\Plex Media Server\Scanners\Series`
4. Copy content of `plex\Plug-ins` to `%LOCALAPPDATA%\Plex Media Server\Plug-ins`
  * `plex\Plug-ins\BMTAgentTVShows.bundle` -> `%LOCALAPPDATA%\Plex Media Server\Plug-ins\BMTAgentTVShows.bundle`
5. Copy `plex\sageplex_cfg.json` to `%LOCALAPPDATA%\Plex Media Server`
  * Edit this file with the appropriate SageTV/PLEX settings
6. Start SageTV and PLEX Media Server.

If installation is successful, you should have the following options
in the Add Library screen in PLEX Media Server:

![add library](https://github.com/ai7/sagetv-for-plexmediacenter/raw/master/image/screenshot1.png)

### Config File

The Scanner/Agent uses a sageplex_cfg.json file for configuration.
This file should be in the root folder of the PLEX data folder.

If for some reason the scanner/agent is not able to locate this file,
or you wish to put it elsewhere, you can set an environment variable
**SAGEPLEX_CFG** to point to this file or the directory where this
file resides.

The value for the environment variable can contain other environment
variables, for example:

```
set SAGEPLEX_CFG=%LOCALAPPDATA%\Plex Media Server
```

#### sageplex_cfg.json ####

```
{
    "sagex": {
        "host"     : "localhost",
        "port"     : 8080,
        "user"     : "enter_username",
        "password" : "enter_password"
    },
    "plex": {
        "host"     : "localhost",
        "port"     : 32400
    },
    "scanner": {
        "ext"      : [".mpg", ".avi", ".mkv", ".mp4", ".ts", ".m4v"],
        "log"      : "%LOCALAPPDATA%\\Plex Media Server\\Logs\\sageplex_scanner.log",
        "debug"    : true
    },
    "agent": {
        "locking"  : true
    }
}
```

## Update

If you already have the plug-in installed, and wish to update the
plugin to a newer version and rescan your library, you can perform the
following additional steps to ensure the rescan will start from a
clean state:

1. Delete the existing SageTV library from your PLEX Media Server.
2. Perform a **Clean Bundles** operation.
3. Perform a **Empty Trash** operation.
4. Stop/Exit PLEX Media Server.
5. Perform the install steps listed above.
6. Start PLEX Media Server

You can optionally clean the Log folder before step 6 if you want to
start from a clean set of logs.

## Troubleshooting

After you install the Plug-in, you can add a Library to PLEX and use
the **SageTV Scanner** as the Scanner and **SageTV BMT Agent (TV
Shows)** as the Agent in the Advanced setting tab.

After you click "Add Library", the scanner will scan the folder for
SageTV recordings and add them to the library. The agent will then
download metadata information and fanart for the recording from
SageTV.

If something doesn't go as expected, you can examine the scanner and
agent logs to see what might have gone wrong.

### Scanner Log

You can find the scanner log file **sageplex_scanner.log** in the PLEX
log folder:

%LOCALAPPDATA%\Plex Media Server\Logs\sageplex_scanner.log

```
2015-04-06 17:10:11,894| DEBUG   | Python 2.7.4 (default, Dec 15 2014, 19:22:01) [MSC v.1800 32 bit (Intel)]
2015-04-06 17:10:11,914| INFO    | ***** Entering SageTV Scanner.Scan *****
2015-04-06 17:10:11,914| DEBUG   | Path: ROOT
2015-04-06 17:10:11,914| DEBUG   | Calling VideoFiles.Scan() ...
...
2015-04-06 17:10:12,367| INFO    | [50/126] Processing F:\SageTV\Scandal-KissKissBangBang-2804046-0.mpg
2015-04-06 17:10:12,367| DEBUG   | Getting media info from SageTV ...
2015-04-06 17:10:12,368| DEBUG   | openUrl: http://sage:frey@localhost:8080/sagex/api?c=plex:GetMediaFileForName&1=Scandal-KissKissBangBang-2804046-0.mpg&encoder=json
2015-04-06 17:10:12,375| DEBUG   | getMediaFileForName(Scandal-KissKissBangBang-2804046-0.mpg): found
2015-04-06 17:10:12,375| DEBUG   | ShowTitle: Scandal
2015-04-06 17:10:12,375| DEBUG   | ShowEpisode: Kiss Kiss Bang Bang
2015-04-06 17:10:12,375| DEBUG   | ShowYear: 
2015-04-06 17:10:12,375| WARNING | Setting show year from OriginalAiringDate: 2014-03-20
2015-04-06 17:10:12,375| DEBUG   | ShowSeasonNumber: 3
2015-04-06 17:10:12,377| DEBUG   | ShowEpisodeNumber: 14
2015-04-06 17:10:12,377| DEBUG   | Creating PLEX Media.Episode object ...
2015-04-06 17:10:12,377| DEBUG   | Media.Episode: Scandal (season 3, episode: 14) => [] starting at 0
2015-04-06 17:10:12,377| DEBUG   | Media file only has 1 segments, done
2015-04-06 17:10:12,377| INFO    | Adding show to mediaList
2015-04-06 17:10:12,377| INFO    | [51/126] Processing F:\SageTV\Scandal-LikeFatherLikeDaughter-3176672-0.mpg
...
2015-04-06 17:10:13,209| INFO    | Total: 126 of 126 added to mediaList
2015-04-06 17:10:13,209| INFO    | Performing Stack.Scan() ...
```

### Agent Log

You can find the agent log file
**com.plexapp.agents.bmtagenttvshows.log** in the PLEX plug-in log
folder:

%LOCALAPPDATA%\Plex Media Server\Logs\PMS Plugin Logs\com.plexapp.agents.bmtagenttvshows.log

```
2015-04-06 17:06:31,289 (1254) :  INFO (logkit:16) - ***** Initializing "SageTV BMT Agent (TV Shows)" *****
2015-04-06 17:06:31,289 (1254) :  INFO (logkit:16) - Config: no env var SAGEPLEX_CFG
2015-04-06 17:06:31,289 (1254) :  INFO (logkit:16) - Config: C:\Users\name\AppData\Local\Plex Media Server\sageplex_cfg.json
2015-04-06 17:06:31,289 (1254) :  INFO (logkit:16) - SAGE_HOST: http://sage:frey@localhost:8080/
2015-04-06 17:06:31,289 (1254) :  INFO (logkit:16) - PLEX_HOST: http://localhost:32400/
2015-04-06 17:06:31,289 (1254) :  INFO (core:609) - Started plug-in
..
2015-04-06 17:07:32,778 (168) :  INFO (logkit:16) - ***** entering BMTAgent.search(Scandal) ***** 
2015-04-06 17:07:32,779 (168) :  DEBUG (logkit:13) - Scandal: adding to search result: MetadataSearchResult(lang='en', thumb=None, score=100, year=None, id='10084', name='Scandal')
..
2015-04-06 17:07:32,841 (17d8) :  INFO (logkit:16) - ***** entering BMTAgent.update(Scandal) ***** 
2015-04-06 17:07:32,841 (17d8) :  INFO (logkit:16) - Scandal/s3/e13: Scandal-NoSunontheHorizon-2791175-0.mpg
2015-04-06 17:07:32,842 (17d8) :  DEBUG (logkit:13) - openUrl: http://sage:frey@localhost:8080/sagex/api?c=plex:GetMediaFileForName&1=Scandal-NoSunontheHorizon-2791175-0.mpg&encoder=json
2015-04-06 17:07:32,854 (17d8) :  DEBUG (logkit:13) - getMediaFileForName(Scandal-NoSunontheHorizon-2791175-0.mpg): found
2015-04-06 17:07:32,854 (17d8) :  INFO (logkit:16) - Scandal/s3/e13: mfid: 2812711
2015-04-06 17:07:32,854 (17d8) :  INFO (logkit:16) - Scandal/s3/e13: setShowSeriesInfo: EP014195350043
2015-04-06 17:07:32,855 (17d8) :  DEBUG (logkit:13) - Scandal/s3/e13: TVDBID: None
..
```

## Build

You can build the zip deliverable by simply run 'make' from the
project root folder. This will create a build directory and package a
zip file with suitable directory structure for install on user system.

To build the project you need to have the following:

1. Python 2.x
2. cxFreeze

## Notes

Many thanks to PiX64 and others who created the initial project on
Google Code, this will not be possible without their efforts.
