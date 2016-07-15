######################################################################
# Author:  PiX(64) - Reid, Michael
#          Raymond Chi
#
# Source:  This scanner was built using code found in Plex Media
#          Scanner.py. Thank you to the plex development team for
#          their help and great starting point.
#
# Purpose: The purpose of SageTV Scanner.py is to provide a means for
#          Plex Media Center to scan SageTV Recording directories.
#          This scanner will find ALL sage recordings including Movies
#          and TV This file used in conjuction with SageTV BMT Scanner
#          (BMTAgent.bundle) will allow users to include sage tv
#          recordings and all BMT scraped metadata into their plex
#          media server setup.
######################################################################

# Reference:
#   https://github.com/plexinc-plugins/Scanners.bundle/blob/master/Contents/Resources/Series/Plex%20Series%20Scanner.py

import re, os, os.path, sys, logging, datetime
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

# --------------------
# regular expression used to find sagetv recordings in the specified directory.
# SageTV files are formated as show-episode-randomnumbers.txt and can
# in some cases include SxxExx information.
# --------------------
# sage_regex = '(?P<show>.*?)-?(([sS])(?P<s_num>[0-9]+)[eE](?P<ep_num>[0-9]+))?-(?P<episode>.*?)-'
# sage_regex = '(?P<show>.*?)-(?P<episode>.*?)-'
#
# The above code is no longer needed, but leaving for reference for now
# --------------------

# Look for episodes.
def Scan(path, files, mediaList, subdirs):
    '''Scan for SageTV TV Shows

    This is called by PLEX for every directory and subdirectories in
    the import folder.

    @param path       path relative to root folder
    @param files      empty list
    @param mediaList  show should be added here
    @param subdirs    list of subdirs under path
    '''
    mylog.info('***** Entering SageTV Scanner.Scan *****')
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
        if not isRecordedTv(mf, airing, showMF):
            continue

        showTitle = showMF.get('ShowTitle').encode('UTF-8')
        mylog.debug('ShowTitle: %s', showTitle)

        episodeTitle = showMF.get('ShowEpisode').encode('UTF-8')
        mylog.debug('ShowEpisode: %s', episodeTitle)

        if not episodeTitle:
            mylog.warning('Using Title as Episode')
            episodeTitle = showTitle

        # Try and get show year, if show year is blank,
        # then try using original airdate, if
        # originalairdate is blank use recordeddate year
        showYear = showMF.get('ShowYear').encode('UTF-8')
        mylog.debug('ShowYear: %s', showYear)

        # always try to get the airDate as we need it later
        airDate = None
        startTime = float(showMF.get('OriginalAiringDate') // 1000)
        recordTime = float(airing.get('AiringStartTime') // 1000)
        if (startTime > 0):
            airDate = datetime.date.fromtimestamp(startTime)
        elif (recordTime > 0):
            airDate = datetime.date.fromtimestamp(recordTime)
        else:
            airDate = datetime.datetime.now()
            mylog.warning('No OriginalAiringDate/AiringStartTime! '
                          'Using today as airDate: %s', airDate)

        if not showYear:
            mylog.warning('Setting show year from airDate: %s', airDate)
            showYear = int(airDate.year)
        else:
            showYear = int(showYear)

        # must convert to int or else Plex throws a
        # serialization exception
        s_num = int(showMF.get('ShowSeasonNumber'))
        mylog.debug('ShowSeasonNumber: %d', s_num)

        # must convert to string or else Plex throws a
        # serialization exception
        ep_num = int(showMF.get('ShowEpisodeNumber'))
        mylog.debug('ShowEpisodeNumber: %d', ep_num)

        # if there is no season or episode number, default
        # it to 0 so that Plex can still pull it in
        if not ep_num:
            # AiringIDs are strictly internal to Wiz.bin and vary from
            # one Sage installation to another. So lets not use it.
            # ep_num = int(airing.get('AiringID'))

            # first try last 4 digit of ShowExternalID. This is what
            # sage uses in its UI and represent zip2it's episode-id.
            mylog.warning('No episode number, trying to set a suitable one ...')
            programId = showMF.get('ShowExternalID')
            if programId:
		mylog.debug('programId: %s', programId)
                # http://forums.schedulesdirect.org/viewtopic.php?f=8&t=41
                # MV+10-12 digits for movies
                # SP+10-12 digits for sports
                # EP+SERIESID+EPISODEID for a series where episode info is known
                # SH+SERIESID+0000 for a series where episode info is *not* known.
                #    SERIESID could be 6 or 8 chars
                ep_num = programId[-4:] # last 4 chars

		#  Handle this little aberration: EPtvdbs00e00
		if ep_num.isdigit():
                    ep_num = str(int(ep_num))
	        else:
                    ep_num = 0

                if ep_num == '0':  # all 0, can't use
                    mylog.warning('ShowExternalID[-4:] is all zero: %s', programId)
                    ep_num = None
                else:
                    mylog.warning('Setting ep_num to ShowExternalID[-4:]: %s', ep_num)
            # next we try airing date
            if not ep_num:
                ep_num = airDate.strftime('%Y%m%d')
                mylog.warning('Setting ep_num to airDate: %s', ep_num)

        if not s_num:
            s_num = showYear
            mylog.warning("Show number is 0, setting to show year: %d", s_num)

        # now we create the Media.Episode object representing this
        # show so we can add it to PLEX.
        mylog.debug('Creating PLEX Media.Episode object ...')
        tv_show = Media.Episode(showTitle, s_num, ep_num, episodeTitle, None)
        mylog.debug("Media.Episode: %s", tv_show)

        tv_show.display_offset = 0  # what's this?

        # need to handle mutliple recordings for the
        # same physical show i.e. -0.mpg, -1.mpg, -2.mpg
        m_seg = mf.get('NumberOfSegments')
        if (m_seg > 1):
            # if show have more than one segment, see if we need to
            # add this to an existing mediaFile object
            mylog.info("Media has more than 1 segment: %s", m_seg)
            # first lookup the show in the current added mediaList, if
            # found, this means we've processed existing segments of
            # the show, so just add the additional segments
            mFound = False
            for mItem in mediaList:
                # is this the right show
                if (mItem.show != showTitle or mItem.season != s_num or
                    mItem.episode != ep_num or mItem.name != episodeTitle):
                    continue
                # found the show, add file to show
                mItem.parts.append(i)  # add to end
                mItem.parts.sort()     # sort file list lexically
                mylog.info('Added to existing mediaList obj: %s', mItem)
                # handled, so break out of search loop
                stat['added'] += 1
                mFound = True
                break
            if mFound:
                # multi-segment and used an existing mediaList object,
                # so done, go to next file. the current tv_show object
                # is discarded.
                continue

        # only one segment, or multi-segment but first time,
        # add the file to the new tv_show object
        tv_show.parts.append(i)

        mylog.info("Adding show to mediaList")
        mediaList.append(tv_show)
        stat['added'] += 1

    # END "for i in files"
    mylog.info('Total: %d of %d added to mediaList',
               stat['added'], stat['size'])

    # only need to do this once at end, not for every file
    if stat['added']:
        mylog.info("Performing Stack.Scan() ...")
        Stack.Scan(path, files, mediaList, subdirs)

    mylog.info('')  # done write empty line so we have good separator for next time

def isRecordedTv(mf, airing, show):
    '''Is this a recorded TV program that we should process

    @param mf      MediaFile obj from sage
    @param airing  mf['Airing']
    @param show    airing['Show']
    @return        True/False
    '''
    # check if this is a sage recording or not
    if not mf.get('IsTVFile'):
        mylog.warning("File is NOT TV recording! skipping")
        return False
    
    #  Check MediaType
    mediaFileMetadataProperties = mf.get("MediaFileMetadataProperties")
    if mediaFileMetadataProperties:
	mylog.debug("Found a MediaFileMetadataProperties.  Getting MediaType")
        mediaType = mediaFileMetadataProperties.get("MediaType")
	if mediaType:
	    if 'Movie' in mediaType:
		mylog.debug("MediaType says Movie, skipping")
		return False
	    else:
		mylog.debug("MediaType is %s, continuing checks...", mediaType)
	else:
	    mylog.debug("MediaType not Found....")
    else:
	mylog.debug("MediaFileMetadataProperties not Found....")

    # now check category
    category = show.get('ShowCategoriesList')
    if not category:
        mylog.warning("No ShowCategoriesList! skipping")
        return False

    if 'Movie' in category:
        mylog.warning("Show is a movie, skipping: %s", category)
        return False

    return True;


if __name__ == '__main__':
    import sys
    print "Hello, world!"
    path = sys.argv[1]
    files = [os.path.join(path, file) for file in os.listdir(path)]
    media = []
    Scan(path[1:], files, media, [])
    print "Media:", media

# useful stuff
# python falsy values: None/False/0/''/{}
# function implicit return: None
