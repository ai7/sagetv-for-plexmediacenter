#####################################################################
#
# Author:  Raymond Chi
#
# Module that handles communication with sageTV server. Work under
# both scanner (standalone python) and agent (PMS framework)
#
# SageTV API: http://sagetv.com/api/
#
######################################################################

import urllib, json, threading

import plexlog  # log wrapper for scanner/agent

DEFAULT_CHARSET = 'utf-8'


def unicodeToStr(obj):
    '''Convert unicode string/array/dict to UTF-8

    @param obj  str/array/dict to be converted
    @return     UTF-8 encoded obj of same type
    '''
    t = obj
    if (t is unicode):
        return obj.encode(DEFAULT_CHARSET)
    elif (t is list):
        for i in range(0, len(obj)):
            obj[i] = unicodeToStr(obj[i])
        return obj
    elif (t is dict):
        for k in obj.keys():
            v = obj[k]
            del obj[k]
            obj[k.encode(DEFAULT_CHARSET)] = unicodeToStr(v)
        return obj
    else:
        return obj # leave numbers and booleans alone


######################################################################
# SageX class
######################################################################

class SageX(object):
    '''Class that handles talking to a sagex service via HTTP interface'''

    def __init__(self, sagexHost, useLock=True, log=None):
        '''Creates a SageX object

        @param sagexHost  url such as http://usr:pwd@host:port/
        @param useLock    whether to synchronize sagex API calls
        @param log        plexlog obj from Agent, or None
        '''
        # setup log
        if log:  # called from agent
            self.log = log
            self.isAgent = True
        else:  # called from scanner, use default (console)
            self.log = plexlog.PlexLog()
            self.isAgent = False
        # set property
        if sagexHost:
            if not sagexHost.endswith('/'):
                sagexHost += '/'
            self.SAGEX_HOST = sagexHost
        else:
            self.SAGEX_HOST = ''
            self.log.error('SageX: sagexHost not specified!!')
        # used to synchronize sagex http call, otherwise may get
        # fanart download problem as PLEX calls Agent.search() and
        # Agent.update() from multiple threads and there seems to be
        # some issue with downloading fanart there.
        self.useLock = useLock
        # self.lock = Thread.Lock('sagexLock')
        self.lock = threading.Lock()

    def openUrl(self, url):
        '''now open the url and get the raw data returned

        @param url  URL to open
        @return     data from server or None
        '''
        # TODO: figure out why sagex needs to be single threaded for
        # all fan art to download correctly.
        fileData = None
        # if self.useLock: Thread.AcquireLock(self.lock)
        if self.useLock: self.lock.acquire()
        try:
            self.log.debug('openUrl: %s', url)
            # we can't use the framework's HTTPRequest() or
            # JSON.ObjectFromURL() because it apparently doesn't know
            # how to deal with url that have user/password
            input = urllib.urlopen(url)
            fileData = input.read()
        except IOError, e:
            self.log.error("openUrl: failed on: %s: %s", url, str(e))
        finally:
            # if self.useLock: Thread.ReleaseLock(self.lock)
            if self.useLock: self.lock.release()

        return fileData


    def getApiUrl(self, func, params, service, encoder):
        '''Generate the URL we need to make the sagex API call

        @param func     sagex API function name
        @param params   [list] of parameters
        @param service  custom service name, or None
        @param encoder  result encoders: xml, json, and nielm
        @return         url for making the sagex API call
        '''
        # first construct the function parameters
        # &1=params[0]&2=params[1]...
        pStr = ''
        i = 1
        for p in params:
            # escape any space in filenames
            pStr += ('&' + str(i)) + '=' + urllib.quote(p)
            i += 1

        # append : to custom service if specified
        if service:
            service += ':'
        else:
            service = ''

        # now construct the URL such as
        # /sagex/api?c=plex:GetMediaFileForName&1=%s&encoder=json
        url = (self.SAGEX_HOST +
               ('sagex/api?c=%s%s%s&encoder=%s' %
                (service, func, pStr, encoder)))
        return url

    def call(self, func, params=[], service='', encoder='json'):
        '''Make a generic sagex API call

        @param func     sagex function to call
        @param params   [list] of parameters for function
        @param service  custom service name
        @param encoder  result encoders: xml, json, and nielm
        @return         result of call as string
        '''
        if not func:
            self.log.error("SageX.call: func is NULL")
            return
        url = self.getApiUrl(func, params, service, encoder)

        # now open the url
        data = self.openUrl(url)
        if not data:
            return

        if encoder != 'json':
            return data

        # now decode json
        try:
            if self.isAgent:
                s1 = JSON.ObjectFromString(data)
            else:
                s1 = json.JSONDecoder().decode(data)
            # is this needed?
            return unicodeToStr(s1)
        except ValueError, e:
            self.log.error("call: json decode failed: %s", str(e))

    # API implemented in plex.js
    def getMediaFileForName(self, filename):
        '''Call the GetMediaFileForName API

        Invoke the GetMediaFileForName API and return the value stored
        under "MediaFile" key. This object contains all SageTV
        properties for this particular episode.

        @param filename  filename to lookup media info
        @return          json[MediaFile] or None
        '''
        # encode into utf8 in case filename contains strange character
        filename = filename.encode(DEFAULT_CHARSET)
        s1 = self.call('GetMediaFileForName', [filename], 'plex')
        if s1:
            val = s1.get('MediaFile') # None if key not found
            self.log.debug('getMediaFileForName(%s): %s', filename,
                           'found' if val else 'not found')
            return val

    # http://download.sage.tv/api/sage/api/ShowAPI.html#GetShowSeriesInfo%28sage.Show%29
    def getShowSeriesInfo(self, showExternalID):
        '''Call the GetShowSeriesInfo API

        Invoke the GetShowSeriesInfo API and return the value stored
        under "SeriesInfo" key. This object contains SageTV
        properties about a particular show series

        @param showExternalID  show id such as EP010855880150
        @return                json[SeriesInfo] or None
        '''
        s1 = self.call('GetShowSeriesInfo',
                       ['show:%s' % showExternalID])
        if s1:
            val = s1.get('SeriesInfo')
            self.log.debug('getShowSeriesInfo(%s): %s', showExternalID,
                           'found' if val else 'not found')
            return val

    # http://download.sage.tv/api/sage/api/MediaFileAPI.html#GetMediaFiles%28%29
    def getMediaFilesForShow(self, showName):
        '''Return the list of media files for a particular show

        Invoke the GetMediaFiles API and filter result using
        GetShowTitle(showName)

        @param showName  show name such as 'Scandal'
        @return          list of media files
        '''
        s1 = self.call('EvaluateExpression',
                       ['FilterByMethod(GetMediaFiles("T"), "GetShowTitle", "%s", true)' %
                        showName])
        if s1:
            val = s1.get('Result') # None if key not found
            self.log.debug('getMediaFilesForShow(%s): %s', showName,
                           'found ' + str(len(val)) if val else 'not found')
            return val


    # http://download.sage.tv/api/sage/api/MediaFileAPI.html#GetMediaFileForID%28int%29
    def getMediaFileForID(self, mediaFileId):
        '''Get a mediaFile based on a mediaFileId

        Returns the MediaFile object that corresponds to the passed in
        ID. The ID should come from the MediaFileID field

        @param mediaFileId  id such as '3517255'
        @return             json[MediaFile] or None
        '''
        s1 = self.call('GetMediaFileForID', [str(mediaFileId)])
        if s1:
            val = s1.get('MediaFile') # None if key not found
            self.log.debug('getMediaFileForID(%s): %s', mediaFileId,
                           'found' if val else 'not found')
            return val

    # https://github.com/stuckless/sagetv-sagex-api/wiki/REST-APIs-using-sagex-api
    def getFanArtUrl(self, artifact, mfid):
        '''Get the URL for retrieving the particular type of fanart

        @param artifact  poster|banner|background|episode
        @param mfid      media file ID
        @return          URL
        '''
        if not (artifact == 'poster' or artifact == 'banner' or
                artifact == 'background' or artifact == 'episode'):
            self.log.error('SageX.getFanArtUrl: invalid artifact specified: %s', artifact)
            return

        url = (self.SAGEX_HOST +
               'sagex/media/fanart?mediafile=%s&artifact=%s' % (mfid, artifact))
        return url

    def getFanArt(self, url):
        '''Request for fanart and check result

        Request a fanart from SageTV. The URL is the one generated by
        getFanArtUrl(). This simply opens the URL and gets the result,
        which should be an image.

        If the fanart is not found, the server will return back an
        HTML page. We look for the beginning <html> tag and return
        None if that is the case

        @param url  URL to open the fanart
        @param      fanart or None
        '''
        # open the url and get the response from server
        response = self.openUrl(url)
        if not response:
            self.log.warning('getFanArt: server returned no data')
            return

        # need to check reply to make sure it is a fanart
        if (response.startswith('<html>') or response.startswith('<HTML>')):
            self.log.warning('getFanArt: <html> detected in fanart response, not fanart')
            return False

        return response

    # /sagex/api?c=ClearWatched&1=airing:3951965&encoder=json
    def clearWatched(self, airing):
        '''Clears the watched information for this Airing completely

        @param airing  SageTV airing ID
        @return        JSON response
        '''
        return self.call('ClearWatched', ['airing:%s' % airing])

    # /sagex/api?c=SetWatched&1=airing:3951965&encoder=json
    def setWatched(self, airing):
        '''Set the watched flag on an Airing

        Sets the watched flag for this Airing to true as if the user
        watched the show from start to finish

        @param airing  SageTV airing ID
        @return        JSON response
        '''
        return self.call('SetWatched', ['airing:%s' % airing])

    # /sagex/api?c=SetWatchedTimes&1=airing:3951965&2=xxxx&3=yyyy&encoder=json
    def setWatchedTimes(self, airing, watchedEndTime, realStartTime):
        '''Updates the Watched information for this airing

        @param airing          SageTV airing ID
        @param watchedEndTime  [ms] an airing-relative time which indicates
                               the time the user has watched the show up until.
        @param realStartTime   [ms] the time (in real time) the user started
                               watching this program at.
        @return                JSON response
        '''
        return self.call('SetWatchedTimes',
                         ['airing:%s' % airing,
                          str(watchedEndTime),
                          str(realStartTime)])


######################################################################

# for testing

def main():
    c = config.Config(sys.platform)
    if len(sys.argv) < 2:
        print 'Usage: <media_file>'
        return
    sagex = SageX(c.getSagexHost())

    # get Mediafile info
    a = sys.argv[1]
    sagex.log.info('********** getMediaFileForName(%s) **********', a)
    mf = sagex.getMediaFileForName(a)
    pprint.pprint(mf)


#if __name__ == '__main__':
#    import sys, logging, pprint
#    import config
#    logging.basicConfig(format='%(asctime)s| %(levelname)-8s| %(message)s',
#                        level=logging.DEBUG)
#    main()

# useful stuff
# python falsy values: None/False/0/''/{}
# function implicit return: None
