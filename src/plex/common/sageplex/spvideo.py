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

START_IGNORE = 60*1000  # ignore starting position under a minute
END_IGNORE   = 20       # ignore ending position within 1/this of ending


class BaseVideo(object):
    '''Base video class with some useful stuff'''

    def __init__(self):
        self.watched = False  # has the show been watched
        self.resume = 0       # resume pos in milliseconds
        self.resumeNorm = 0   # normalized resume pos in ms
        self.duration = 0     # show length in ms
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

    def getResumeNorm(self):
        '''Return normalized resume position in ms

        A normalized resume position have value 0 if the show has been
        watched, or within 1 min of start or 5% of ending. This makes
        it easy for us to compare resume position without requiring
        complicated logic to handle differences between how Sage and
        PLEX handles watched shows, and corner cases.
        '''
        return self.resumeNorm

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
        self.watchedStartTime = 0  # in ms
        self.watchedEndTime = 0    # in ms
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
            self.lastWatched = int(data // 1000)  # store in SECOND

        # get show duration
        data = airing.get('AiringDuration')  # in ms
        if data:
            self.duration = int(data)

        # get resume position
        data = airing.get('WatchedDuration')  # in ms
        if data:
            self.resume = int(data)
            # set normalized resume position
            self.setResumeNorm()

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

        # Sage's LatestWatchedTime seems to track WatchedEndTime,
        # which is not the real timestamp the user has last watched
        # the show. So we override it with realEndTime here
        if self.realWatchedEndTime > self.lastWatched * 1000:
            self.lastWatched = self.realWatchedEndTime // 1000

    def __str__(self):
        '''Return string representation if implicitly requested'''
        # lastwatched / resume
        s = self.getLastWatchedStr() + ' / ' + self.getResumeStr()
        if self.watched:
            s += ' [watched]'
        else:
            s += ' [not watched]'
        return s

    def setResumeNorm(self):
        '''Compute the normalized resume position for Sage

        For Sage, if a show is watched, then the resume position is
        left as is, either at the very end, or very close to the end.
        We simply normalize it back to 0.

        If a position is less than 1m from start, set it back to 0.

        We don't need to handle the 5% from ending case for Sage
        because Sage will leave the pos at the end when we finish
        watching, and clear watched status when you rewatch, so
        there's no ambuigity on when Sage considers a show watched.
        '''
        val = self.resume
        if self.watched:
            # if status is watched, set pos back to 0
            if val > 0:
                val = 0
        elif val > 0 and val < START_IGNORE:
            # if pos is within 1 min, set back to 0
            val = 0
        self.resumeNorm = val

    def getInfo(self, detail=False):
        '''Return detailed timing info if requested

        @param detail  whether detailed info is wanted or not
        @return        string
        '''
        s = str(self)
        if not detail:
            return s

        # return detailed timing info formatted for screen
        if self.watchedStartTime and self.watchedEndTime:
            s += ('\n\t\t%s to %s [%s] (Watched Time)' %
                  (self.timeToStr(self.watchedStartTime // 1000),
                   self.timeToStr(self.watchedEndTime // 1000),
                   self.durationToStr((self.watchedEndTime -
                                       self.watchedStartTime) // 1000)))
        # real start/end if exist
        if self.realWatchedStartTime and self.realWatchedEndTime:
            s += ('\n\t\t%s to %s [%s] (Real Watched Time)' %
                  (self.timeToStr(self.realWatchedStartTime // 1000),
                   self.timeToStr(self.realWatchedEndTime // 1000),
                   self.durationToStr((self.realWatchedEndTime -
                                       self.realWatchedStartTime) // 1000)))
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

        # XXX: get show duration
        self.duration = int(node.get('duration', 0))

        # get the viewOffset, ie, resume position, this is in ms
        self.resume = int(node.get('viewOffset', 0))
        # set normalized resume position
        self.setResumeNorm()

        # the view count can be quite big on PLEX for some reason
        self.viewCount = int(node.get('viewCount', 0))
        if self.viewCount:
            self.watched = True
        else:
            self.watched = False

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

    def setResumeNorm(self):
        '''Compute the normalized resume position for PLEX'''
        val = self.resume
        if val > 0 and val < START_IGNORE:
            # if pos is within 1 min, set back to 0. PLEX does not
            # allow setting of resume pos within 1 min anyway.
            val = 0
        if val:
            # if pos is within 5% of ending, set back to 0. we do this
            # because we don't know when exactly PLEX considers a show
            # watched, so this is an approximation.
            diff = abs(self.duration - val)
            if diff <= (self.duration / END_IGNORE):
                val = 0
        self.resumeNorm = val

    def getInfo(self):
        '''Get resume timing information'''
        s = ''
        if self.lastWatched or self.resume:
            s += ('%s / %s' % (self.getLastWatchedStr(),
                               self.getResumeStr()))
        if self.watched:
            s += ' [watched %s]' % str(self.viewCount)
        else:
            s += ' [not watched]'
        return s

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
