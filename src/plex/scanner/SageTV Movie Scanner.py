#####################################################################
# Author:  PiX(64) - Reid, Michael
#          Raymond Chi
#
# Source:  This scanner was built using code found in Plex Media
#          Scanner.py. Thank you to the plex development team for
#          their help and great starting point.
#
# Purpose: The purpose of SageTV Movie Scanner.py is to provide a
#          means for Plex Media Center to scan SageTV Recording
#          directories. This scanner will find ALL sage recordings
#          including Movies recorded by sage and movies sage knows
#          about. This file used in conjuction with SageTV BMT
#          Scanner (BMTAgent.bundle) will allow users to include sage
#          tv recordings and all BMT scraped metadata into their plex
#          media server setup.
######################################################################

# Reference:
#   https://github.com/plexinc-plugins/Scanners.bundle/blob/master/Contents/Resources/Movies/Plex%20Movie%20Scanner.py

import re, os, os.path, sys, logging
import Media, VideoFiles, Stack, Utils

LOG_FORMAT = '%(asctime)s| %(levelname)-8s| %(message)s'

####################

# note: Plex will load the sageplex module from the Movie Scanner's
#       folder instead of from the TV Scanner's folder due to the way
#       plex organizes python import folders.

import sageplex.plexlog # log wrapper for scanner/agent
import sageplex.config  # handles sageplex configuration file
import sageplex.sagex   # handles sagex API to SageTV

logging.basicConfig(format=LOG_FORMAT, level=logging.DEBUG)  # use console
sageplexcfg = sageplex.config.Config(sys.platform)  # create Config object

# setup logging, slightly complicated because initially we log to console,
# after the config object is read, we update logging to the new logfile
mylog = sageplex.plexlog.PlexLog()  # log wrapper
mylog.updateLoggingConfig(sageplexcfg.getScannerLog(), LOG_FORMAT,
                          sageplexcfg.getScannerDebug())

mylog.debug('Python ' + sys.version)

####################


# Look for episodes.
def Scan(path, files, mediaList, subdirs):
    '''Scan for SageTV Movies

    This is called by PLEX for every directory and subdirectories in
    the import folder.

    @param path       path relative to root folder
    @param files      empty list
    @param mediaList  show should be added here
    @param subdirs    list of subdirs under path

    '''
    mylog.info('***** Entering SageTV Movie Scanner.Scan *****')
    mylog.debug('Path: ' + (path if path else 'ROOT'))

    # create sagex obj for SageTV API call
    sagexHost = sageplexcfg.getSagexHost()
    sageapi = sageplex.sagex.SageX(sagexHost)
    
    # scans the current dir and return the list files for processing.
    # files that have already been processed will not be returned.
    mylog.debug('Calling VideoFiles.Scan() ...');
    VideoFiles.Scan(path, files, mediaList, subdirs, None) # Scan for video files.
    if not files:
        mylog.info('No files returned, done')
        mylog.info('')  # done write empty line so we have good separator for next time
        return

    # stat we track while in loop
    stat = { 'item': 0,
             'size': len(files),
             'added': 0}

    # interate over all files found in VideoFiles.Scan above
    for i in files:
        # i contains the full path to the file
        stat['item'] += 1
        mylog.info('[%d/%d] Processing %s', stat['item'], stat['size'], i)

        filename = os.path.basename(i)
        (fname, fext) = os.path.splitext(filename)

        # if the extension is in our list of acceptable sagetv file extensions, then process
        if not fext.lower() in sageplexcfg.getScannerExt():
            mylog.info('wrong extension, skipping: %s', fext)
            continue

        # Get SageTV media info from sagex via HTTP call
        mylog.debug('Getting media info from SageTV ...')
        mf = sageapi.getMediaFileForName(filename)
        if not mf:
            # this would happen if there is a file on the Plex import
            # directory but that file is not yet in Sage's DB
            mylog.error("No media info from SageTV: %s", filename)
            continue

        # retrieving the airing/show field that should always exist
        airing = mf.get('Airing')
        if not airing:
            mylog.error('no Airing field, skipping file');
            continue
        showMF = airing.get('Show')
        if not showMF:
            mylog.error('no [Airing][Show] field, skipping file');
            continue

        # check to see if TV show or not
        if not isRecordedMovie(mf, airing, showMF):
            continue

        showTitle = showMF.get('ShowTitle').encode('UTF-8')
        mylog.debug('ShowTitle: %s', showTitle)

        showYear = showMF.get('ShowYear').encode('UTF-8')
        mylog.debug('ShowYear: %s', showYear)
        if not showYear:
            showYear = ''

        # now we create the Media.Movie object representing this
        # movie so we can add it to PLEX.
        movie = Media.Movie(showTitle, showYear)
        movie.source = VideoFiles.RetrieveSource(filename)
        movie.parts.append(i)

        mylog.info("Adding show to mediaList")
        mediaList.append(movie)
        stat['added'] += 1

    # END "for i in files"
    mylog.info('Total: %d of %d added to mediaList',
               stat['added'], stat['size'])

    # only need to do this once at end, not for every file
    if stat['added']:
        mylog.info("Performing Stack.Scan() ...")
        Stack.Scan(path, files, mediaList, subdirs)

    mylog.info('')  # done write empty line so we have good separator for next time

def isRecordedMovie(mf, airing, show):
    '''Is this a recorded movie that we should process

    @param mf      MediaFile obj from sage
    @param airing  mf['Airing']
    @param show    airing['Show']
    @return        True/False
    '''
    # check if this is a sage recording or not
    if not mf.get('IsTVFile'):
        mylog.warning("File is NOT TV recording! skipping")
        return False

    # now check category
    category = show.get('ShowCategoriesList')
    if not category:
        mylog.warning("No ShowCategoriesList! skipping")
        return False

    if not ('Movie' in category):
        mylog.warning("Show is NOT a movie, skipping: %s", category)
        return False

    return True;

    
# useful stuff
# python falsy values: None/False/0/''/{}
# function implicit return: None
