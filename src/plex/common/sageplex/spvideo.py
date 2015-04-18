#####################################################################
#
# Author:  Raymond Chi
#
# Module with wrapper class for SageTV and Plex Video objects
#
######################################################################

import datetime, os


######################################################################
# base Video class
######################################################################

class BaseVideo(object):
    '''Base video class with some useful stuff'''

    def __init__(self):
        self.watched = False  # has the show been watched
        self.resume = 0       # resume pos in milliseconds
        self.lastWatched = 0  # last watched in seconds

    def timeToStr(self, time):
        '''Convert a time in seconds to a string

        @param time  time in seconds
        @return      string representation of time
        '''
        if time:
            s = str(datetime.datetime.fromtimestamp(time))
        else:
            s = ''
        return s

    def durationToStr(self, time):
        '''Convert a duration in seconds to string

        @param time  time in seconds
        @return      stringn representation of elapsed time
        '''
        return str(datetime.timedelta(seconds=time))

    def getResume(self):
        '''Return resume position in ms'''
        return self.resume

    def getResumeStr(self, default=''):
        '''Return the resume position as a string'''
        if self.resume:
            return self.durationToStr(self.resume // 1000)
        else:
            return default

    def getWatched(self):
        '''Whether show has been watched or not'''
        return self.watched

    def getLastWatchedStr(self):
        '''Return last watched as a string'''
        return self.timeToStr(self.lastWatched)


######################################################################
# SageVideo class
######################################################################

class SageVideo(BaseVideo):
    '''Class that represents a SageTV video object'''

    def __init__(self, mf, log):
        '''Creates a SageVideo object from a MediaFile object

        @param mf   obj from sagex getMediaFileForName()
        @param log  log object for debug
        '''
        # initialize base class
        # agent environment don't have super(), so use this
        BaseVideo.__init__(self)
        # super(SageVideo, self).__init__()

        # initialize additional defaults
        self.realWatchedStartTime = 0  # in ms
        self.realWatchedEndTime = 0    # in ms

        # get Airing/Show which is essential
        airing = mf.get('Airing')
        if not airing:
            log.error('Sage MediaFile object has no Airing attribute')
            return
        show = airing.get('Show')
        if not show:
            log.error('Sage MediaFile object has no Show attribute')
            return

        # has this show been watched?
        self.watched = airing.get('IsWatched')

        # get the last watched time
        data = airing.get('LatestWatchedTime')  # in ms
        if data:
            self.lastWatched = int(data // 1000)

        # get resume position
        data = airing.get('WatchedDuration')  # in ms
        if data:
            self.resume = int(data)

        # get the watched start and end time, this should corresponds
        # to the latest watched time and the watched duration above
        start = airing.get('WatchedStartTime')  # ms
        end = airing.get('WatchedEndTime')  # ms
        if start and end:
            self.watchedStartTime = int(start)
            self.watchedEndTime = int(end)

        # get the RealWatchedStartTime and RealWatchedEndTime. this
        # could span months in some cases if you started watching a
        # show but stopped and later resumed a few month later.
        start = airing.get('RealWatchedStartTime')  # ms
        end = airing.get('RealWatchedEndTime')  # ms
        if start and end:
            self.realWatchedStartTime = int(start)
            self.realWatchedEndTime = int(end)

    def __str__(self):
        '''Return string representation if implicitly requested'''
        # lastwatched / resume
        s = self.getLastWatchedStr() + ' / ' + self.getResumeStr()
        # real start/end if exist
        #if self.realWatchedStartTime and self.realWatchedEndTime:
        #    s += (' (%s to %s [%s])' %
        #          (self.timeToStr(self.realWatchedStartTime // 1000),
        #           self.timeToStr(self.realWatchedEndTime // 1000),
        #           self.durationToStr((self.realWatchedEndTime -
        #                               self.realWatchedStartTime) // 1000)))
        return s


######################################################################
# PlexVideo class
######################################################################

class PlexVideo(BaseVideo):
    '''Class that represents a PLEX video object'''

    def __init__(self, node, log):
        '''Creates a PlexVideo object from a XML <Video> element.

        @param node  XML <video> element object
        @param log   log object for debug
        '''
        # initialize base class
        # agent environment don't have super(), so use this
        BaseVideo.__init__(self)
        # super(PlexVideo, self).__init__()

        # initialize additional defaults
        self.file = ''

        # sanity check
        TAG_TYPE = 'Video'
        if node.tag != TAG_TYPE:
            log.error('PlexVideo: expect <%s> but got: <%s>',
                      TAG_TYPE, node.tag)
            return

        # first get title, should always exist.
        # this could have chars that can't be printed
        self.title = node.get('title')

        # when toggling watched/unwatched in plex UI, the backend sets
        # the following attr: viewCount="1" lastViewedAt="1428970566".
        #
        # When the show is imported to PLEX via the BMT agent and has
        # been watched, the lastViewedAt is set to the import
        # date/time as that's when the watched status is toggled on.

        # get the lastViewedAt, in seconds
        self.lastWatched = int(node.get('lastViewedAt', 0))

        # get the viewOffset, ie, resume position, this is in ms
        self.resume = int(node.get('viewOffset', 0))

        # get the filename
        p = node[0][0]  # Media/Part, this seems more reliable than .find()
        if p.tag == 'Part':
            self.file = os.path.basename(p.get('file'))
            # now set the plex media id
            self.id = node.get('ratingKey')

    def __str__(self):
        '''Return string representation if implicitly requested'''
        s= ('%s: %s' % (self.id, self.getTitle()))
        return s

    def getInfo(self):
        '''Get resume timing information'''
        if self.lastWatched or self.resume:
            return ('%s / %s' % (self.getLastWatchedStr(),
                                 self.getResumeStr()))
        else:
            return ''

    def getTitle(self):
        '''Return the title, ASCII safe'''
        if self.title:
            # print will fail on non-ascii
            return self.title.encode('ascii', 'replace')
        else:
            return ''


# useful stuff
# python falsy values: None/False/0/''/{}
# function implicit return: None
