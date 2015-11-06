# sageplex_sync Utility

SageTV and PLEX watch status synchronization Tool

## Overview

This is a command line tool to synchronize the watch status and resume
position of shows between SageTV and PLEX Media Server.

Two way synchronization is performed. More recent watch status
metadata will be used.

```
c:\>sageplex_sync.exe -h
usage: sageplex_sync.py [options] [id [id ...]]

positional arguments:
  id                    PLEX library ID/name/all (default: None)

optional arguments:
  -h, --help            show this help message and exit
  -l, --list            list PLEX library sections (default: False)
  -s, --sync            sync watch status (default: False)
  -m, --media           ID is media-id, not section-id (default: False)
  --sagedata            dump SageTV data for media-id (default: False)
  --position POSITION   Set explicit resume position (h:m:s) (default: None)
  -x IGNORE             ignore if pos within initial x seconds (default: 60)
  -p                    confirm each sync update (default: False)
  -n                    do nothing, simulate sync operation (default: False)
  --addtv NAME [PATH ...]
                        add PLEX library for Sage TV shows (default: False)
  --addmovie NAME [PATH ...]
                        add PLEX library for Sage Movies (default: False)
  --delsec ID           delete a PLEX library section (default: None)
  --refresh ID          refresh a PLEX library section (default: None)

Compare or synchronize watch status and resume position of the
specified PLEX library sections with SageTV. Individual PLEX Media
files can be specified when the -m option is used. ```

## Download

This tool is available in the `plex\synctool` folder of the download
zip file. It can be run directly from this folder, no special
installation is required.

## Invoking

For windows, a `.exe` is provided. For MacOS/Linux, the source Python
script is provided and can be run directly on those platforms.

This tool uses the same `sageplex_cfg.json` configuration file as the
SageTV Scanner/BMT Agent.

### Windows

```
win32\sageplex_sync.exe
```

### MacOS/Linux

```
python python/sageplex_sync.py
```

## Usage Example

Here are some usage examples to get your started:

### Synchronize Everything

This command will synchronize all your PLEX libraries with SageTV:

```
sageplex_sync.exe all -s
```

If you want to synchronize a particular file or particular library, or
get synchronization status without synchronizing, check out the
example below.

### List PLEX Libraries

This command will list your PLEX libraries. You can use the library-id
or name to limit the synchronization to that library.

```
sageplex_sync.exe -l
```

### Check/Synchronize PLEX Library

To check the sync status of all shows for a particular PLEX library,
run the following command:

```
sageplex_sync.exe LIBRARY
```

This will display synchronization status of all shows in the specified
PLEX library, but will not perform the actual synchronization.

A summary page will be shown at the end of the output. This gives you
an opportunity to inspect the result before performing the actual
synchronization.

A PLEX Media ID is also shown for each show found. This ID can be used
to limit the check/sync operation to that particular show only.

To perform the actual synchronization, run the same command, but with a
`-s` option on the command line:

```
sageplex_sync.exe LIB_ID -s
```

### Check/Synchronize One Particular Show

You can also check/synchronize a particular show. Simply use the
show MEDIA-ID and pass the `-m` flag to indicate the ID is a media-id,
not a library-id.

```
sageplex_sync.exe -m MEDIA-ID
sageplex_sync.exe -m MEDIA-ID -s
```

## Notes on Synchronization

SageTV and PLEX Media Server differs in how they track watch status
and resume position. This tool takes these differences into
consideration to avoid unnecessary synchronization operations.

### SageTV

When you finish watching a show, or watch a show close enough to the
end, SageTV will tag the show as watched, and leave the resume
position at the end.

When you watch a show again, the watched status is cleared, and the
resume position restarts from the beginning.

### PLEX

When you finish watching a show, or watch a show close enough to the
end, PLEX will increment the watched count for the show, and resets
the resume position back to the beginning.

When you watch a show again, the watched count remains, and the resume
position starts to advance from the beginning.

### SyncTool

The synchronization tool takes these differences into consideration,
and will consider the show as being in-sync if it's in a watched state
on both systems.

Furthermore, any resume position less than a minute, or within 5% of
ending, is ignored. This ensures the synchronization logic is
compatible with both systems.
