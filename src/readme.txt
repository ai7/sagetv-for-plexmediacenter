Folder Description

+--plex                                 files for Plex Media Server
|  +--agent                             custom Agent for PMS
|  |  +--BMTAgentMovies.bundle          agent for SageTV movies
|  |  |  \--Contents
|  |  |     +--Code
|  |  |     \--Resources
|  |  \--BMTAgentTVShows.bundle         agent for SageTV recordings
|  |     \--Contents
|  |        +--Code
|  |        \--Resources
|  +--common                            common agent/scanner code
|  |  \--sageplex                       module name
|  \--scanner                           custom Scanner for PMS
\--sagetv                               files for SageTV
   \--sagex-services                    custom service for sagex

Run 'make' at the root folder will produce a build directory with
content suitable for install on user system.
