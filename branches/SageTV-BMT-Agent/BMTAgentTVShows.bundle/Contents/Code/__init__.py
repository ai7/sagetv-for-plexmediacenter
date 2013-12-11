import re, datetime, unicodedata, hashlib, types, urllib, os, simplejson as json
from datetime import date

SAGEX_HOST = ""
PLEX_HOST = ""

DEFAULT_CHARSET = 'utf-8'

def Start():
  HTTP.CacheTime = CACHE_1HOUR * 24 
    
def unicodeToStr(obj):
  t = obj
  if(t is unicode):
    return obj.encode(DEFAULT_CHARSET)
  elif(t is list):
    for i in range(0, len(obj)):
      obj[i] = unicodeToStr(obj[i])
    return obj
  elif(t is dict):
    for k in obj.keys():
      v = obj[k]
      del obj[k]
      obj[k.encode(DEFAULT_CHARSET)] = unicodeToStr(v)
    return obj
  else:
    return obj # leave numbers and booleans alone
	
def executeSagexAPICall(url, resultToGet):
	#Log.Debug('*** sagex request URL: %s' % url)
	try:
		input = urllib.urlopen(url)
	except IOError, i:
		Log.Debug("ERROR in executeSagexAPICall: Unable to connect to SageTV server")
		return None
	fileData = input.read()
	resp = unicodeToStr(json.JSONDecoder().decode(fileData))

	objKeys = resp.keys()
	numKeys = len(objKeys)
	if(numKeys == 1):
		return resp.get(resultToGet)
	else:
		return None
  
def getShowSeriesInfo(showExternalID):
	url = SAGEX_HOST + '/sagex/api?c=GetShowSeriesInfo&1=show:%s&encoder=json' % showExternalID
	resp = executeSagexAPICall(url, 'SeriesInfo')
	return resp
  
def getMediaFilesForShow(showName):
	parameter = ', "GetShowTitle", "%s", ' % showName
	url = SAGEX_HOST + '/sagex/api?c=EvaluateExpression&1=FilterByMethod(GetMediaFiles("T")%strue)&encoder=json' % parameter
	Log.Debug("UNQUOTED getMediaFilesForShow URL=%s" % url)
	url = SAGEX_HOST + '/sagex/api?c=EvaluateExpression&1=FilterByMethod(GetMediaFiles("T")%strue)&encoder=json' % urllib.quote(parameter)
	Log.Debug("QUOTED getMediaFilesForShow URL=%s" % url)
	return executeSagexAPICall(url, 'Result')
  
def getMediaFileForID(mediaFileID):
	url = SAGEX_HOST + '/sagex/api?c=GetMediaFileForID&1=%s&encoder=json' % mediaFileID
	Log.Debug('**** URL to Call = %s' % url)
	return executeSagexAPICall(url, 'MediaFile')
  
def getMediaFileForFilePath(filename):
	url = SAGEX_HOST + '/sagex/api?c=plex:GetMediaFileForName&1=%s&encoder=json' % filename
	Log.Debug('**** URL to Call = %s' % url)
	return executeSagexAPICall(url, 'MediaFile')
  
def getFilenameOnly(filepathAndName):
	if(filepathAndName.find("\\")<0):
		return filepathAndName[filepathAndName.rfind("/")+1:len(filepathAndName)]
	else:
		return filepathAndName[filepathAndName.rfind("\\")+1:len(filepathAndName)]

def readPropertiesFromPropertiesFile():
	global SAGEX_HOST, PLEX_HOST
	try:
		cwd = os.getcwd()
		Log.Debug('***cwdddddddddddd=%s' % cwd)
		if(cwd.find("\\") >=0): #backslashes are typically from windows machines
			cwd = cwd.replace("\\\\?\\", "")
			cwd = cwd.replace("Plug-in Support\\Data\\com.plexapp.agents.bmtagenttvshows", "Plug-ins\\BMTAgentTVShows.bundle\\Contents\\Code\\")
		elif(len(cwd) == 1): #for some reason on Macs, CWD returns just a forward slash /
			cwd = "~/Library/Application Support/Plex Media Server/Plug-ins/BMTAgentTVShows.bundle/Contents/Code/"
		elif(cwd.find("/") >=0): #forward slashes are typically from non-windows machines
			cwd = cwd.replace("Plug-in Support/Data/com.plexapp.agents.bmtagenttvshows", "Plug-ins/BMTAgentTVShows.bundle/Contents/Code/")

		propertiesFilePath = cwd + "BMTAgent.properties"
		Log.Debug('***propertiesFilePath=%s' % propertiesFilePath)
		if(os.path.isfile(propertiesFilePath)):
			f = os.open(propertiesFilePath, os.O_RDONLY)
		else:
			return False
		# Read all input from the properties file
		fileInput = ""
		c = os.read(f, 1)
		while c != "":
			fileInput = fileInput + c
			c = os.read(f, 1)
		
		lines = fileInput.split('\n')
		for keyValuePair in lines:
			keyValues = keyValuePair.split('=')
			Log.Debug('***Properties file key=%s; value=%s' % (keyValues[0], keyValues[1]))
			if(keyValues[0] == "SAGEX_HOST"):
				SAGEX_HOST = keyValues[1]
			elif(keyValues[0] == "PLEX_HOST"):
				PLEX_HOST = keyValues[1]
		
	except:
		return False
	
	os.close(f)
	return True
  
def setWatchedUnwatchedFlag(id, isWatched):
	Log.Debug('*** setWatchedUnwatchedFlagsetWatchedUnwatchedFlag: id=%s;isWatched=%s' % (id, str(isWatched)))
	if(isWatched):
		# If sage says it's watched, set it as watched in Plex
		url = PLEX_HOST + '/:/scrobble?key=%s&identifier=com.plexapp.plugins.library' % id
	else:
		url = PLEX_HOST + '/:/unscrobble?key=%s&identifier=com.plexapp.plugins.library' % id
	Log.Debug('*** PLEX request URL: %s' % url)
	try:
		input = urllib.urlopen(url)
	except IOError, i:
		Log.Debug("ERROR in setWatchedUnwatchedFlag: Unable to connect to PMS server")
		return False
	return True
  
def getFanart(url):
	try:
		response = urllib.urlopen(url)
		fileData = response.read()
	except IOError, i:
		Log.Debug("ERROR in getFanart: Unable to download fanart at the following URL: %s" % url)
		return None
	return fileData

class BMTAgent(Agent.TV_Shows):
  name = 'SageTV BMT Agent (TV Shows)'
  languages = [Locale.Language.English]
  primary_provider = True
  contributes_to = None
  accepts_from = ['com.plexapp.agents.plexthememusic']

  def search(self, results, media, lang, manual=False):
	#filename = media.items[0].parts[0].file.decode('utf-8')
	Log.Debug("****STARTTTTTTTT")
	if(not readPropertiesFromPropertiesFile()):
		Log.Debug("****UNABLE TO READ BMTAGENT.PROPERTIES FILE... aborting search")
	
	quotedFilepathAndName = media.filename
	Log.Debug('****media.id=%s; media.filename=%s' % (str(media.id), quotedFilepathAndName))
	unquotedFilepathAndName = urllib.unquote(quotedFilepathAndName)
	# Pull out just the filename to use
	unquotedFilename = getFilenameOnly(unquotedFilepathAndName)
	Log.Debug('****unquotedFilepathAndName=%s' % unquotedFilepathAndName)
	Log.Debug('****unquotedFilename=%s' % unquotedFilename)
	(filename, ext) = os.path.splitext(unquotedFilename)
	Log.Debug('****filename = %s' % filename)
	mf = getMediaFileForFilePath(filename)
	
	if(mf): # this would only return false if there is a file on the Plex import directory but that file is not yet in Sage's DB
		airing = mf.get('Airing')
		show = airing.get('Show')
		# Check if the Sage recording is a movie or film; if it is, ignore it (workaround for user is to move movies out to a separate import directory that Plex can read an import as Movie content vs. TV Show content
		category = show.get('ShowCategoriesString')
		if(category.find("Movie")<0 and category.find("Movies")<0 and category.find("Film")<0):
			Log.Debug('***1) AiringStartTime = %s' % airing.get('AiringStartTime'))
			if (airing.get('AiringStartTime')):
				startTime = airing.get('AiringStartTime') // 1000
				airDate = date.fromtimestamp(startTime)
			#Log.Debug('***1) airdate = %s' % airDate)
			mfid = str(mf.get('MediaFileID'))
			results.Append(MetadataSearchResult(id=mfid, name=media.show, score=100, lang=lang, year=airDate.year))
		else:
			Log.Debug('***Movies/Movies/Film found, ignoring and will not call update; categorylist=%s' % category)

  def update(self, metadata, media, lang):
	Log.Debug('***UPDATE CALLEDDDDDDDDDDDDDDDDDDDDDDDD')
	if(not readPropertiesFromPropertiesFile()):
		Log.Debug("****UNABLE TO READ BMTAGENT.PROPERTIES FILE... aborting search")

	mfid = str(metadata.id)
	mf = getMediaFileForID(mfid)		
	#Log.Debug("***mfid = %s " % mf)
	airing = mf.get('Airing')
	show = airing.get('Show')
	extrainfo = mf.get('MediaFileMetadataProperties')
	showExternalID = show.get('ShowExternalID')
	
	series = getShowSeriesInfo(showExternalID)

	#Set the Show level metadata
	Log.Debug("series=%s" % str(series))
	metadata.title = show.get('ShowTitle')
	thetvdbid = extrainfo.get('MediaProviderDataID')
	if (thetvdbid):
		metadata.id = thetvdbid
	else:
		metadata.id = ""		
	Log.Debug("****TVDBID = %s" % str(thetvdbid))

	metadata.title_sort = metadata.title
	if(series):
		metadata.summary = series.get('SeriesDescription')

	else:
		metadata.summary = show.get('ShowDescription')

	metadata.studio = airing.get('Channel').get('ChannelNetwork')		
	
	if (airing.get('AiringStartTime')):
		startTime = airing.get('AiringStartTime') // 1000
		airDate = date.fromtimestamp(startTime)
		metadata.originally_available_at = airDate
	
	metadata.duration = airing.get('AiringDuration')
	metadata.content_rating = str(airing.get('ParentalRating'))[:2] + '-' + str(airing.get('ParentalRating'))[2:]
	cats = show.get('ShowCategoriesString')
	metadata.genres.clear()
	metadata.genres.add(cats)
		
	Log.Debug("METADATA.ID = %s", extrainfo.get('MediaProviderDataID'))
	Log.Debug("COMPLETED SETTING SERIES-LEVEL METADATA;metadata.title=%s;metadata.summary=%s;metadata.originally_available_at=%s;metadata.studio=%s" % (metadata.title, metadata.summary, metadata.originally_available_at, metadata.studio))

	# Set the metadata for all episode's in each of the season's
	mfs = getMediaFilesForShow(metadata.title)
	for seasonNum in media.seasons:
		season = metadata.seasons[seasonNum]
		for episodeNum in media.seasons[seasonNum].episodes:
			Log.Debug("LOOKING FOR METADATA FOR metadata.seasons[%s].episodes[%s]" % (seasonNum, episodeNum))
			episode = metadata.seasons[seasonNum].episodes[episodeNum]
			for mf in mfs:
				mediaFileID = mf.get('MediaFileID')
				airing = mf.get('Airing')
				if(airing):
					show = airing.get('Show')
					if(show):
						plexFilename = getFilenameOnly(media.seasons[seasonNum].episodes[episodeNum].items[0].parts[0].file)
						mfFilenames = mf.get('SegmentFiles')
						for mfFilename in mfFilenames:
							mfFilename = getFilenameOnly(mfFilename)
							#Log.Debug("mfFilename=%s;plexFilename=%s" % (str(mfFilename), plexFilename))
							(plexName, plexExt) = os.path.splitext(plexFilename)
							(sageName, sageExt) = os.path.splitext(mfFilename)
							if(plexName == sageName):
								#Log.Debug("****plexName = %s" % plexName)
								#Log.Debug("****sageName = %s" % sageName)
								Log.Debug("SHOW OBJECT FOR MATCHED SHOW: %s" % str(show))
								Log.Debug("UPDATING METADATA FOR SEASON: %s; EPISODE: %s" % (seasonNum, episodeNum))
								Log.Debug('***2) AiringStartTime = %s' % airing.get('AiringStartTime'))
								
								if (airing.get('AiringStartTime')):
									startTime = airing.get('AiringStartTime') // 1000
									airDate = date.fromtimestamp(startTime)

								Log.Debug('***2) airdate = %s' % airDate)

								episode.title = show.get('ShowEpisode')
								if(episode.title == None or episode.title == ""):
									episode.title = show.get('ShowTitle')
								episode.summary = show.get('ShowDescription')
								episode.originally_available_at = airDate
								episode.duration = airing.get('AiringDuration')
								episode.season = int(seasonNum)

								stars = show.get('PeopleListInShow')
								episode.guest_stars.clear()
								for star in stars:
									episode.guest_stars.add(star)

								background_url = SAGEX_HOST + '/sagex/media/fanart?mediafile=%s&artifact=background' % mediaFileID
								poster_url = SAGEX_HOST + '/sagex/media/fanart?mediafile=%s&artifact=poster' % mediaFileID
								banner_url = SAGEX_HOST + '/sagex/media/fanart?mediafile=%s&artifact=banner' % mediaFileID

								#Set Season urls
								season_poster_url = SAGEX_HOST + '/sagex/media/fanart?mediafile=%s&artifact=poster' % (mediaFileID)
								season_background_url = SAGEX_HOST + '/sagex/media/fanart?mediafile=%s&artifact=background' % (mediaFileID)
								season_banner_url = SAGEX_HOST + '/sagex/media/fanart?mediafile=%s&artifact=banner' % (mediaFileID)
								thumb_url = SAGEX_HOST + '/sagex/media/fanart?mediafile=%s&artifact=episode' % (mediaFileID)								
								
								#if (show.get('SeasonNumber') is None):
								#	season_poster_url = poster_url
								#	season_banner_url = banner_url
								#	#thumb_url= SAGEX_HOST + '/sagex/media/fanart?mediafile=%s&artifact=episode' % (mediaFileID)
								#	thumb_url = SAGEX_HOST + '/sagex/media/fanart?mediafile=%s&artifact=episode' % (mediaFileID)
								#else:
								#	season_poster_url = SAGEX_HOST + '/sagex/media/fanart?mediafile=%s&artifact=poster&season=%s' % (mediaFileID,seasonNum)
								#	season_background_url = SAGEX_HOST + '/sagex/media/fanart?mediafile=%s&artifact=background&season=%s' % (mediaFileID,seasonNum)
								#	season_banner_url = SAGEX_HOST + '/sagex/media/fanart?mediafile=%s&artifact=banner&season=%s' % (mediaFileID,seasonNum)
								#	thumb_url = SAGEX_HOST + '/sagex/media/fanart?mediafile=%s&artifact=episode' % (mediaFileID)

								#Log.Debug("***posterurl = %s && season poster = %s" % (poster_url,season_poster_url))

								#First check if the poster is already assigned before adding it again to top level tvshow element
								if not metadata.posters:
									metadata.posters[poster_url] = Proxy.Media(getFanart(str(poster_url)))
								if not metadata.art:
									metadata.art[background_url] = Proxy.Media(getFanart(str(background_url)))
								if not metadata.banners:
									metadata.banners[banner_url] = Proxy.Media(getFanart(str(banner_url)))

								#Set season and episode level fanart
								#First check if the poster is already assigned before adding it again
								
								if not season.posters:
									season.posters[poster_url] = Proxy.Media(getFanart(str(season_poster_url)))
								if not season.banners:
									season.banners[banner_url] = Proxy.Media(getFanart(str(season_banner_url)))
								if not episode.thumbs:
									episode.thumbs[thumb_url] = Proxy.Media(getFanart(str(thumb_url)))
								
								#Log.Debug("episode.thumbs = %s" % (str(episode.thumbs)))
								#Log.Debug("**show parental rating = %s" % str(airing.get('ParentalRating')))
								episode.content_rating = str(airing.get('ParentalRating'))[:2] + '-' + str(airing.get('ParentalRating'))[2:]
								
								Log.Debug('*** callingggggggg: id=%s' % media.id)
								setWatchedUnwatchedFlag(str(media.seasons[seasonNum].episodes[episodeNum].id), airing.get('IsWatched'))
								
								mfprops = mf.get('MediaFileMetadataProperties')
								episode.guest_stars.add(show.get('PeopleInShow'))
								episode.writers.add(mfprops.get('Writer'))
								episode.directors.add(mfprops.get('Director'))
								episode.producers.add(mfprops.get('ExecutiveProducer'))
								
								Log.Debug("COMPLETED SETTING EPISODE-LEVEL METADATA FOR SEASON: %s; EPISODE: %s;;;;episode.title=%s;episode.summary=%s;episode.originally_available_at=%s;episode.duration=%s;episode.season=%s;metadata.content_rating=%s;" % (seasonNum, episodeNum, episode.title, episode.summary, episode.originally_available_at, episode.duration, episode.season, metadata.content_rating))
								
								break