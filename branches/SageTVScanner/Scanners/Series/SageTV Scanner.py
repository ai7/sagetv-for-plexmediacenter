######################################################################
# Author: PiX(64) - Reid, Michael
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

import re, os, os.path, urllib
import Media, VideoFiles, Stack, Utils

from datetime import date

# write log to file until we figure out a better way
import logging
logging.basicConfig(level=logging.DEBUG,
                    filename='e:/plexscan.log',
                    format='%(asctime)s| %(module)s| %(levelname)-8s| %(message)s')

import SageX  # my sagex API object

# Enter ip address and port http://x.x.x.x:port
# or if you server requires user/pass enter http://user:pass@x.x.x.x:port
# SAGEX_HOST = 'http://x.x.x.x:port'
SAGEX_HOST = 'http://sage:frey@localhost:8080'

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
    '''Scan for SageTV TV Shows'''
    logging.info('***** Entering SageTV Scanner.Scan *****')

    sagex = SageX.SageX(url=SAGEX_HOST)  # create sagex obj

    logging.debug('Calling VideoFiles.Scan() ...');
    VideoFiles.Scan(path, files, mediaList, subdirs, None) # Scan for video files.

    item_no = 0
    files_size = len(files)

    # interate over all files found in VideoFiles.Scan above
    for i in files:
        # i contains the full path to the file
        item_no += 1
        logging.info('[%d/%d] Processing %s', item_no, files_size, i)

        filename = os.path.basename(i)
        (fname, fext) = os.path.splitext(filename)

        if not fext.lower() in ['.mpg', '.avi', '.mkv', '.mp4', '.ts', '.m4v']:
            logging.info('wrong extension, skipping: %s', fext)
            continue

        # Get SageTV media info from sagex via HTTP call
        logging.debug('Getting media info from SageTV ...')
        mf = sagex.GetMediaFileForName(filename)
        if not mf:
            # this would happen if there is a file on the Plex import
            # directory but that file is not yet in Sage's DB
            logging.error("No media info from SageTV: %s", filename)
            continue

        # retrieving the airing/show field that should always exist
        airing = mf.get('Airing')
        if not airing:
            logging.error('no Airing field, skipping file');
            continue
        showMF = airing.get('Show')
        if not showMF:
            logging.error('no [Airing][Show] field, skipping file');
            continue

        showTitle = showMF.get('ShowTitle').encode('UTF-8')
        logging.debug('ShowTitle: %s', showTitle)

        episodeTitle = showMF.get('ShowEpisode').encode('UTF-8')
        logging.debug('ShowEpisode: %s', episodeTitle)

        if not episodeTitle:
            logging.warning('Using Title as Episode')
            episodeTitle = showTitle

        # Try and get show year, if show year is blank,
        # then try using original airdate, if
        # originalairdate is blank use recordeddate year
        showYear = showMF.get('ShowYear').encode('UTF-8')
        logging.debug('ShowYear: %s', showYear)
        if not showYear:
            startTime = float(showMF.get('OriginalAiringDate') // 1000)
            recordTime = float(airing.get('AiringStartTime') // 1000)
            if (startTime > 0):
                airDate = date.fromtimestamp(startTime)
                logging.warning('Setting show year from OriginalAiringDate: %s', airDate)
                showYear = int(airDate.year)
            elif (recordTime > 0):
                airDate = date.fromtimestamp(recordTime)
                logging.warning('Setting show year from AiringStartTime: %s', airDate)
                showYear = int(airDate.year)
            else:
                showYear = 2012  # TODO: better default?
                logging.warning('Setting show year to default: %d', 2015)
        else:
            showYear = int(showYear)

        # must convert to int or else Plex throws a
        # serialization exception
        s_num = int(showMF.get('ShowSeasonNumber'))
        logging.debug('ShowSeasonNumber: %d', s_num)

        # must convert to string or else Plex throws a
        # serialization exception
        ep_num = int(showMF.get('ShowEpisodeNumber'))
        logging.debug('ShowEpisodeNumber: %d', ep_num)

        # if there is no season or episode number, default
        # it to 0 so that Plex can still pull it in
        if not ep_num:
            ep_num = int(airing.get('AiringID'))
            logging.warning('No episode number, setting ep_num to AiringID: %d', ep_num)
        if not s_num:
            s_num = showYear
            logging.warning("Show number is 0, setting to show year: %d", s_num)

        # TODO: this test is wrong but Ok for here I suppose
        category = showMF.get('ShowCategoriesString')
        logging.debug('ShowCategories: %s', category)
        if not (category.find("Movie") < 0 and
                category.find("Movies") < 0 and
                category.find("Film") < 0):
            logging.warning("File is Movie or Film! skipping")
            continue

        # now we create the Media.Episode object representing this
        # show so we can add it to PLEX.
        logging.debug('Creating PLEX Media.Episode object ...')
        tv_show = Media.Episode(showTitle, s_num, ep_num, episodeTitle, None)
        logging.debug("Media.Episode: %s", tv_show)

        tv_show.display_offset = 0  # what's this?

        # need to handle mutliple recordings for the
        # same physical show i.e. -0.mpg, -1.mpg, -2.mpg
        valid = False
        m_seg = mf.get('NumberOfSegments')
        if (m_seg > 1):
            logging.info("Media has more than 1 segment: %s", m_seg)
            # x = Saturtday Night Live (season 01, Episode 27) => ['path']
            counter = 0
            for value in mediaList:
                if (value.show == showTitle and
                    value.name == episodeTitle and
                    value.season == s_num and
                    value.episode == ep_num):
                    if (value.parts[0] < i):
                        logging.info("value.parts[0] less than currnet file. "
                                     "Current file goes at [1]. [0] = %s" %
                                     mediaList[counter].parts[0])
                        mediaList[counter].parts.append(i)
                        valid = True
                        logging.info("new mediaList = %s" % mediaList)
                        break
                    elif (value.parts[0] > i):
                        logging.info("value.parts[0] greater than current file. "
                                     "Set [1] = [0] and [0] = i")
                        mediaList[counter].parts.insert(0,i)
                        valid = True
                        break
                # Current show not yet found increment and continue
                counter += 1
            # END "for value in mediaList"
            # We have a file with mutliple segments,
            # and looped through entire mediaList. Not
            # current in mediaList so add
            if not valid:
                logging.warning("We have a file with mutliple parts in bmt, "
                                "but not currently in media list. "
                                "Adding to mediaLiost")
                tv_show.parts.append(i)
        else:
            # Show only has 1 segment. Append
            logging.debug("Media file only has 1 segments, done")
            tv_show.parts.append(i)

        if valid:
            # multi-segment and handled, so done
            continue

        logging.info("Adding show to mediaList")
        mediaList.append(tv_show)

    # END "for i in files"

    # only need to do this once at end, not for every file
    logging.info("Performing Stack.Scan() ...")
    Stack.Scan(path, files, mediaList, subdirs)

    logging.info('')  # done write empty line so we have good separator for next time


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
