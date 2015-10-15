#
# SageTV BMT Agent (TV Shows)
#
# This file implements a PMS agent plug-in that adds metadata to files
# found by the SageTV Scanner. It queryings sagex on SageTV server to
# fill in the show information and download the appropriate fan arts.
#
# Plex Plug-in Framework documentation
#   https://dev.plexapp.com/docs/
#
# Note: This runs inside the PMS framework's runtime environment. The
#       environment is different from from regular Python program, and
#       certain restrictions apply. For example, functions name cannot
#       begin with _. For details, see the plug-in documentation above.
#

import urllib, os

import plexlog              # log wrapper
import config               # handles sageplex_cfg.json configuration
import sagex                # handles communication with SageTV
import plexapi              # api for misc plex function
import spvideo              # parsing sage/plex video object

mylog    = None
myconfig = None
mysagex  = None
myplex   = None


def Start():
    '''This function is called when the plug-in first starts. It can be
    used to perform extra initialisation tasks such as configuring the
    environment and setting default attributes.
    '''
    global mylog, myconfig, mysagex, myplex
    mylog = plexlog.PlexLog(isAgent=True)  # use Log instead of logging

    mylog.info('***** Initializing "SageTV BMT Agent (TV Shows)" *****')
    HTTP.CacheTime = CACHE_1HOUR * 24

    # PMS supports a DefaultPrefs.json file for plug-ins, and settings
    # can be accessed via simple Prefs['id'].
    #
    # The problem is, after the 1st run, settings are stored per plugin
    # in an XML file in the "plug-in support folder":
    #  plug-in support\preferences\com.plexapp.agents.bmtagenttvshows.xml
    # This makes updating the setting by the user a little confusing,
    # as there are 2 places to change.
    #
    # using a standalone json file for both scanner/agent is easier
    # for the user to understand and manage.
    myconfig = config.Config(Platform.OS, log=mylog)
    sagexHost = myconfig.getSagexHost()
    mylog.info('SAGE_HOST: %s', sagexHost)
    plexHost = myconfig.getPlexHost()
    mylog.info('PLEX_HOST: %s', plexHost)

    # create the SageX object from sagex module
    mysagex = sagex.SageX(sagexHost,
                          useLock=myconfig.getAgentLocking,
                          log=mylog)
    # create plex api object
    myplex = plexapi.PlexApi(plexHost, log=mylog)


class BMTAgent(Agent.TV_Shows):
    '''This is the agent class representing SageTV BMT Agent'''

    # A string defining the name of the agent for display in the GUI.
    # This attribute is required.
    name = 'SageTV BMT Agent (TV Shows)'

    # A list of strings defining the languages supported by the agent.
    # These values should be taken from the constants defined in the
    # Locale API. This attribute is required.
    languages = [Locale.Language.English]

    # A boolean value defining whether the agent is a primary metadata
    # provider or not. Primary providers can be selected as the main
    # source of metadata for a particular media type.
    primary_provider = True

    # A list of strings containing the identifiers of agents that can
    # contribute secondary data to primary data provided by this
    # agent. This attribute is optional.
    # accepts_from = ['com.plexapp.agents.plexthememusic']

    # A list of strings containing the identifiers of primary agents
    # that the agent can contribute secondary data to. This attribute
    # is optional.
    # contributes_to = None

    # https://dev.plexapp.com/docs/agents/search.html
    def search(self, results, media, lang, manual):
        '''Searching for results to provide matches for media

        When the media server needs an agent to perform a search, it
        calls the agent's search method.

        should use the hints provided by the media object to add a
        series of search result objects to the provided results
        object. Results should be instances of the
        MetadataSearchResult class.

        This is called once for each Show.

        @param results  An empty container that the developer should
                        populate with potential matches.
        @param media    An object containing hints to be used when
                        performing the search.
        @param lang     A string identifying the user's currently
                        selected language.
        @param manual   Whether the search was issued automatically
                        or manually by user.
        '''
        # media contains: (not all fields shown)
        # {'filename': 'G%3A%5Csagetest%5CScandal-KissKissBangBang-2804046-0%2Empg',
        #  'show': 'Scandal',
        #  'season': '3',
        #  'episode': '14',
        #  'name': 'Kiss Kiss Bang Bang',
        #  'episodic': '1',
        #  'id': '9351'}
        mylog.info("***** entering BMTAgent.search(%s) ***** ", media.show)

        # simply add media to search result, no need to do anything.
        #
        # originally this contained quite a bit of code, the main
        # purpose being to extract an mfid from sagetv based on
        # media.filename, and store it in the MetadataSearchResult.id
        # field. The update() function can then retrieve the media
        # from Sage given the mfid recorded here.
        #
        # But this is not necessary. In update(), the media object
        # contains the filename for all the seasons and episodes.
        # We can use that to do lookup in sage directly.
        msr = MetadataSearchResult(id=media.id, name=media.show,
                                   score=100, lang=lang)
        mylog.debug('%s: adding to search result: %s', media.show, msr)
        results.Append(msr)

    # https://dev.plexapp.com/docs/agents/update.html
    def update(self, metadata, media, lang):
        '''Adding metadata to media

        Once an item has been successfully matched, it is added to the
        update queue. As the framework processes queued items, it
        calls the update method of the relevant agents.

        This is called once for each Show. The function should craw
        through all the seasons/episodes and set the appropriate
        attribute on each one.

        @param metadata  A pre-initialized metadata object if this is
                         the first time the item is being updated, or
                         the existing metadata object if the item is
                         being refreshed.
        @param media     An object containing information about the
                         media hierarchy in the database.
        @param lang      A string identifying the user's currently
                         selected language.
        '''
        # use a local mylog object as this function is called from
        # different threads and we want the log header (that is stored
        # inside the mylog object) to be unique for each call.
        mylog = plexlog.PlexLog(isAgent=True)

        mylog.info("***** entering BMTAgent.update(%s) ***** ", media.title)

        if media and metadata.title is None: metadata.title = media.title

        # Show/Series info is set when we encounter 1st episode below
        seriesInfo = False

        # now set information for each episode in each season
        for s in media.seasons:

            season = metadata.seasons[s]
            season.index = int(s)

            for e in media.seasons[s].episodes:

                episode = metadata.seasons[s].episodes[e]
                episodeMedia = media.seasons[s].episodes[e].items[0]
                # the file for episode is available from the media
                # object, no need to use mysagex.getMediaFilesForShow
                epFile = os.path.basename(episodeMedia.parts[0].file)
                # set a log prefix such as: "showname/s5/e11: "
                mylog.setPrefix('%s/s%s/e%s: ' % (metadata.title, s, e))
                mylog.info('%s', epFile)

                # get the MediaFile object from sage
                mf = mysagex.getMediaFileForName(epFile)
                if not mf:
                    # this should not happen
                    mylog.error("no media info from SageTV")
                    continue

                mediaFileID = mf.get('MediaFileID')
                mylog.info('mfid: %s', mediaFileID)

                # retrieving the airing/show field that should always exist
                airing = mf.get('Airing')
                if not airing:
                    mylog.error('no Airing field, skipping file');
                    continue
                show = airing.get('Show')
                if not show:
                    mylog.error('no [Airing][Show] field, skipping file');
                    continue

                # set series info if we haven't done so already
                if not seriesInfo:
                    if self.setShowSeriesInfo(metadata, media, mf, mylog):
                        seriesInfo = True

                # TODO: move the following episode setter to own function?
                mylog.info('setting episode level metadata')
                if (airing.get('AiringStartTime')):
                    startTime = airing.get('AiringStartTime') // 1000
                    airDate = Datetime.FromTimestamp(startTime)

                mylog.debug('airdate: %s', airDate)

                episode.title = show.get('ShowEpisode')
                if not episode.title:
                    episode.title = show.get('ShowTitle')
                episode.summary = show.get('ShowDescription')
                episode.originally_available_at = airDate
                episode.duration = airing.get('AiringDuration')
                episode.season = int(s)

                stars = show.get('PeopleListInShow')
                episode.guest_stars.clear()
                if stars:  # See issue #13
                    for star in stars:
                        episode.guest_stars.add(star)
                else:
                    mylog.debug('no PeopleListInShow data.')

                # set rating
                rSource = airing.get('ParentalRating')
                rTarget = rSource[:2] + '-' + rSource[2:]
                mylog.debug('rating: %s -> %s', rSource, rTarget)
                episode.content_rating = rTarget

                # set watch flag and resume position
                self.setWatchStatus(mf, airing, media, s, e, mylog)

                # misc stuff
                mfprops = mf.get('MediaFileMetadataProperties')
                episode.guest_stars.add(show.get('PeopleInShow'))
                episode.writers.add(mfprops.get('Writer'))
                episode.directors.add(mfprops.get('Director'))
                episode.producers.add(mfprops.get('ExecutiveProducer'))

                # set the fanart for show and episode
                self.setFanArt(metadata, season, episode, mediaFileID, mylog)

                mylog.debug("COMPLETED SETTING EPISODE-LEVEL METADATA: "
                            "episode.title=%s;episode.summary=%s;"
                            "episode.originally_available_at=%s;episode.duration=%s;"
                            "episode.season=%s;metadata.content_rating=%s;" %
                            (episode.title, episode.summary,
                             episode.originally_available_at, episode.duration,
                             episode.season, metadata.content_rating))


    def setShowSeriesInfo(self, metadata, media, mf, mylog):
        '''Set information about the Show based on a Sage MediafileID

        This sets information about the show (a TV series) based on
        the mfid of a particular episode.

        @param metadata  metadata from update() method
        @param media     media from update() method
        @param mf        MediaFile object from sage
        @param mylog     local log wrapper with appropriate header set
        @return          True on success
        '''
        # retrieving the airing/show field that should always exist
        airing = mf.get('Airing')
        if not airing:
            mylog.error('setShowSeriesInfo: no Airing field, skipping file');
            return
        show = airing.get('Show')
        if not show:
            mylog.error('setShowSeriesInfo: no [Airing][Show] field, skipping file');
            return

        # get showid like EP010855880150
        showExternalID = show.get('ShowExternalID')
        if not showExternalID:
            mylog.error('no ShowExternalID');
            return
        mylog.info('setShowSeriesInfo: %s', showExternalID)

        extrainfo = mf.get('MediaFileMetadataProperties')
        thetvdbid = extrainfo.get('MediaProviderDataID')
        mylog.debug("TVDBID: %s", thetvdbid)
        if thetvdbid:
            metadata.id = thetvdbid  # overwrite id with thetvdbid, why?

        # get the show's information from sagetv
        series = mysagex.getShowSeriesInfo(showExternalID)
        if series:
            metadata.summary = series.get('SeriesDescription')
        else:
            metadata.summary = show.get('ShowDescription')
        mylog.debug("metadata.summary: %s", metadata.summary)

        metadata.studio = airing.get('Channel').get('ChannelNetwork')
        mylog.debug("metadata.studio: %s", metadata.studio)

        # now set the show's starting date. we first use the season
        # premier date on the season object if available. otherwise we
        # use the show's original air date or airing start time.
        seasonStartSet = False
        if series:
            premierDate = series.get('SeriesPremiereDate')
            if premierDate:
                # use the show premier date if available
                airDate = Datetime.ParseDate(premierDate)
                metadata.originally_available_at = airDate
                mylog.debug("metadata.originally_available_at: %s",
                            premierDate)
                seasonStartSet = True
        if not seasonStartSet:
            # next we try the show's metadata
            startTime = show.get('OriginalAiringDate')
            recordTime = airing.get('AiringStartTime')
            if startTime:
                airDate = Datetime.FromTimestamp(startTime // 1000)
                mylog.info('Setting show starting from OriginalAiringDate: %s', airDate)
                metadata.originally_available_at = airDate
            elif recordTime:
                airDate = Datetime.FromTimestamp(recordTime // 1000)
                mylog.info('Setting show starting from AiringStartTime: %s', airDate)
                metadata.originally_available_at = airDate
            else:
                mylog.error('No OriginalAiringDate/AiringStartTime!')

        metadata.duration = airing.get('AiringDuration')
        mylog.debug("metadata.duration: %s", metadata.duration)

        # set rating
        rSource = airing.get('ParentalRating')
        rTarget = rSource[:2] + '-' + rSource[2:]
        metadata.content_rating = rTarget
        mylog.debug('metadata.content_rating: %s', rTarget)

        # set category, add each category individually
        cats = show.get('ShowCategoriesList')
        metadata.genres.clear()
        for cat in cats:
            metadata.genres.add(cat)
        mylog.debug('metadata.genres: %s', cats)

        mylog.debug("COMPLETED SETTING SERIES-LEVEL METADATA: "
                    "metadata.title=%s;metadata.summary=%s;"
                    "metadata.originally_available_at=%s;metadata.studio=%s" %
                    (metadata.title, metadata.summary,
                     metadata.originally_available_at, metadata.studio))
        return True

    def setFanArt(self, metadata, season, episode, mediaFileID, mylog):
        '''Set show and episode fanart

        @param metadata
        @param season
        @param episode
        @param mediaFileID
        @param mylog
        '''
        # set fanart, format is
        #   /sagex/media/fanart?title=ShowName&mediatype=tv|movie|music&
        #     artifact=poster|banner|background&artifactTitle=&season=#&
        #     overwrite=true|false&transform=json_transform&
        #     scalex=#&scaley=#&tag=web&mediafile=sageid|filename

        poster_url     = mysagex.getFanArtUrl('poster', mediaFileID)
        background_url = mysagex.getFanArtUrl('background', mediaFileID)
        banner_url     = mysagex.getFanArtUrl('banner', mediaFileID)

        # Set Season urls
        season_poster_url     = poster_url
        season_background_url = background_url
        season_banner_url     = banner_url
        thumb_url             = mysagex.getFanArtUrl('episode', mediaFileID)

        # first set fanart for the show (not season/episode)
        if not metadata.posters:
            faPoster = mysagex.getFanArt(poster_url)
            if faPoster:
                mylog.debug('setting metadata.posters')
                metadata.posters[poster_url] = Proxy.Media(faPoster)
        else:
            mylog.debug('metadata.posters already has data')

        if not metadata.art:
            faBackground = mysagex.getFanArt(background_url)
            if faBackground:
                mylog.debug('setting metadata.art')
                metadata.art[background_url] = Proxy.Media(faBackground)
        else:
            mylog.debug('metadata.art already has data')

        if not metadata.banners:
            faBanner = mysagex.getFanArt(banner_url)
            if faBanner:
                mylog.debug('setting metadata.banners')
                metadata.banners[banner_url] = Proxy.Media(faBanner)
        else:
            mylog.debug('metadata.banners already has data')

        # now we set fanart for season
        if not season.posters:
            faPoster = mysagex.getFanArt(season_poster_url)
            if faPoster:
                mylog.debug('setting season.posters')
                season.posters[poster_url] = Proxy.Media(faPoster)
        else:
            mylog.debug('season.posters already has data')

        if not season.banners:
            faBanner = mysagex.getFanArt(season_banner_url)
            if faBanner:
                mylog.debug('setting season.banners')
                season.banners[banner_url] = Proxy.Media(faBanner)
        else:
            mylog.debug('season.banners already has data')

        # finally we set it for the show
        if not episode.thumbs:
            faThumb = mysagex.getFanArt(thumb_url)
            if faThumb:
                mylog.debug('setting episode.thumbs')
                episode.thumbs[thumb_url] = Proxy.Media(faThumb)
        else:
            mylog.debug('episode.thumbs already has data')

    def setWatchStatus(self, mf, airing, media, s, e, mylog):
        '''Set watched/unwatched and resume position

        @param mf
        @param airing
        @param media
        @param s
        @param e
        @param mylog   local copy with header
        '''
        sv = spvideo.SageVideo(mf, mylog)
        mylog.debug('IsWatched: %s', sv.getWatched())
        # first set the watched status, we need to do this first
        # before resume position as setting this will clear any resume
        # position on file.
        myplex.setWatched(media.seasons[s].episodes[e].id,
                          sv.getWatched())
        # now set the resume position
        s_resume = sv.getResume()
        if not sv.getResume():
            return
        mylog.debug('WatchedDuration: %s [%s]',
                    sv.getResume(), sv.getResumeStr())
        one_min = 60*1000
        # if pos is within 1 min, ignore, as plex will ignore it
        if s_resume <= one_min:
            mylog.debug('ignoring resume position under 1 minute')
            return
        # if pos is less 1 min of ending
        airingDuration = airing.get('AiringDuration')
        if airingDuration:
            # ignore ending resume position depending on show length
            airingDuration = int(airingDuration)
            diff = airingDuration - s_resume
            if airingDuration <= 60*one_min:
                # for 30/60 minute show, ignore last 2 minute
                if diff <= 2 * one_min:
                    mylog.debug('ignoring resume position 2 min from ending')
                    return
            else:
                # anything longer ignore last 5%
                if diff <= (airingDuration*.05):
                    mylog.debug('ignoring resume position 5% from ending')
                    return
        else:
            mylog.warning('no AiringDuration field!')
        # all OK, set it
        myplex.setProgress(media.seasons[s].episodes[e].id, s_resume)


# useful stuff
# python falsy values: None/False/0/''/{}
# function implicit return: None
