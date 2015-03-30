######################################################################
# Author:  PiX(64) - Reid, Michael
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

import re, os, os.path
import Media, VideoFiles, Stack, Utils

import SageX  # my sagex API object

# Enter ip address and port http://x.x.x.x:port
# or if you server requires user/pass enter http://user:pass@x.x.x.x:port
# SAGEX_HOST = 'http://x.x.x.x:port'
SAGEX_HOST = 'http://sage:frey@localhost:8080'

# Look for episodes.
def Scan(path, files, mediaList, subdirs):
    '''Scan for SageTV Movies'''
    
    sagex = SageX.SageX(url=SAGEX_HOST)  # create sagex obj

    VideoFiles.Scan(path, files, mediaList, subdirs, None) # Scan for video files.

    # loop used to interate over all files found in VideoFiles.Scan above
    for i in files:

        file = os.path.basename(i)
        (file, ext) = os.path.splitext(file)
        print "*** Found File name = %s%s, Start looking for metadata" % (file,ext)

        # if the extension is in our list of acceptable sagetv file extensions, then process
        if not ext.lower() in ['.mpg', '.avi', '.mkv', '.mp4', '.ts', '.m4v']:
            print "******NO MATCH FOUND BY SCANNER!"
            continue

        # Get SageTV media info from sagex via HTTP call
        mf = sagex.GetMediaFileForName(file + ext)
        if not mf:
            # this would happen if there is a file on the Plex import
            # directory but that file is not yet in Sage's DB
            print "****** Current file (%s%s) was not found in BMT!)" % (file,ext)
            continue

        airing = mf.get('Airing')
        showMF = airing.get('Show')
        if not showMF:
            print "****** Current file (%s%s) did not return a valid MEdiaFile Object from BMT" % (file,ext)
            continue
            
        category = showMF.get('ShowCategoriesString')
        showTitle = showMF.get('ShowTitle').encode('UTF-8')
        showYear = showMF.get('ShowYear').encode('UTF-8')

        if not showYear:
            showYear = ''

        # TODO: this is the wrong test, movies shows up as
        # 'Adventure / Fantasy' so the test will fail
        if (category.find("Movie") < 0 and
            category.find("Movies") < 0 and
            category.find("Film") < 0):
            print "****** Current file (%s%s) is a TVShow" % (file,ext)
            continue

        # create PLEX Movie object
        movie = Media.Movie(showTitle, showYear)
        movie.source = VideoFiles.RetrieveSource(file)
        movie.parts.append(i)
        mediaList.append(movie)
        # Stack the results.
        Stack.Scan(path, files, mediaList, subdirs)
        print "****** Current file (%s%s) successfully added to stack!" % (file,ext)
