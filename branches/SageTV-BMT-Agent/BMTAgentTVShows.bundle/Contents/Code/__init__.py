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
	return executeSagexAPICall(url, 'MediaFile')
  
def getMediaFileForFilePath(filename):
	#url = SAGEX_HOST + '/sagex/api?c=GetMediaFileForFilePath&1=%s&encoder=json' % filename
	url = SAGEX_HOST + '/sagex/api?c=plex:GetMediaFileForName&1=%s&encoder=json' % filename
	return executeSagexAPICall(url, 'MediaFile')
  
def getFilenameOnly(filepathAndName):
	if(filepathAndName.find("\\")<0):
		return filepathAndName[filepathAndName.rfind("//")+1:len(filepathAndName)]
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
  accepts_from = None
  #fallback_agent = False
  #accepts_from = 'com.plexapp.agents.thetvdb'
  #contributes_to = ['com.plexapp.agents.thetvdb']
		
  def search(self, results, media, lang, manual):
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
	mf = getMediaFileForFilePath(unquotedFilename)
	
	if(mf): # this would only return false if there is a file on the Plex import directory but that file is not yet in Sage's DB
		airing = mf.get('Airing')
		show = airing.get('Show')
		
		# Check if the Sage recording is a movie or film; if it is, ignore it (workaround for user is to move movies out to a separate import directory that Plex can read an import as Movie content vs. TV Show content
		category = show.get('ShowCategoriesString')
		if(category.find("Movie")<0 and category.find("Movies")<0 and category.find("Film")<0):
			startTime = float(show.get('OriginalAiringDate') // 1000)
			airDate = date.fromtimestamp(startTime)
			mfid = str(mf.get('MediaFileID'))
			results.Append(MetadataSearchResult(id=mfid, name=media.show, score=100, lang=lang, year=airDate.year))
		else:
			Log.Debug('***Movies/Movies/Film found, ignoring and will not call update; categorylist=%s' % category)

  def update(self, metadata, media, lang, force):
	Log.Debug('***UPDATE CALLEDDDDDDDDDDDDDDDDDDDDDDDD')
	mfid = str(metadata.id)
	mf = getMediaFileForID(mfid)
	showExternalID = mf.get('Airing').get('Show').get('ShowExternalID')
	
	series = getShowSeriesInfo(showExternalID)

	#Set the Show level metadata
	if(series):
		Log.Debug("series=%s" % str(series))
		metadata.title = series.get('SeriesTitle')
		metadata.title_sort = metadata.title
		metadata.summary = series.get('SeriesDescription')
		seriesPremiere = series.get('SeriesPremiereDate')
		Log.Debug('***seriesPremiere=%s' % seriesPremiere)
		airDate = datetime.datetime.strptime(seriesPremiere, '%Y-%m-%d')
		Log.Debug('***airDate=%s' % str(airDate))
		metadata.originally_available_at = airDate
		metadata.studio = series.get('SeriesNetwork')
		cats = series.get('SeriesCategory')
		metadata.genres.clear()
		metadata.genres.add(cats)
	else: #No series object exists, pull from the mediafile object
		Log.Debug("SERIES INFO NOT FOUND; PULLING SERIES LEVEL METADATA FROM THE MEDIAFILE OBJECT INSTEAD")
		airing = mf.get('Airing')
		show = airing.get('Show')
		metadata.title = show.get('ShowTitle')
		metadata.title_sort = metadata.title
		metadata.studio = airing.get('AiringChannelName')
		cats = show.get('ShowCategoriesString')
		metadata.genres.clear()
		metadata.genres.add(cats)
		
	Log.Debug("COMPLETED SETTING SERIES-LEVEL METADATA;metadata.title=%s;metadata.summary=%s;metadata.originally_available_at=%s;metadata.studio=%s" % (metadata.title, metadata.summary, metadata.originally_available_at, metadata.studio))

	# Set the metadata for all episode's in each of the season's
	mfs = getMediaFilesForShow(metadata.title)
	for seasonNum in media.seasons:
		season = metadata.seasons[seasonNum]
		for episodeNum in media.seasons[seasonNum].episodes:
			Log.Debug("LOOKING FOR METADATA FOR metadata.seasons[%s].episodes[%s]" % (seasonNum, episodeNum))
			if(episodeNum):
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
								Log.Debug("mfFilename=%s;plexFilename=%s" % (str(mfFilename), plexFilename))
								if(plexFilename == mfFilename):
									Log.Debug("SHOW OBJECT FOR MATCHED SHOW: %s" % str(show))
									Log.Debug("UPDATING METADATA FOR SEASON: %s; EPISODE: %s" % (seasonNum, episodeNum))
									startTime = float(show.get('OriginalAiringDate') // 1000)
									airDate = date.fromtimestamp(startTime)

									episode.title = show.get('ShowEpisode')
									episode.summary = show.get('ShowDescription')
									episode.originally_available_at = airDate
									episode.duration = mf.get('FileDuration')
									episode.season = int(seasonNum)

									stars = show.get('PeopleListInShow')
									episode.guest_stars.clear()
									for star in stars:
										episode.guest_stars.add(star)

									background_url = SAGEX_HOST + '/sagex/media/background/%s' % mediaFileID
									poster_url = SAGEX_HOST + '/sagex/media/poster/%s' % mediaFileID
									banner_url = SAGEX_HOST + '/sagex/media/banner/%s' % mediaFileID
									thumb_url = SAGEX_HOST + '/sagex/media/thumbnail/%s' % mediaFileID

									#First check if the poster is already assigned before adding it again
									if poster_url not in metadata.posters:
										metadata.posters[poster_url] = Proxy.Media(getFanart(poster_url))
									if background_url not in metadata.art:
										metadata.art[background_url] = Proxy.Media(getFanart(background_url))
									if banner_url not in metadata.banners:
										metadata.banners[banner_url] = Proxy.Media(getFanart(banner_url))

									#Set season and episode level fanart
									#First check if the poster is already assigned before adding it again
									if poster_url not in season.posters:
										season.posters[poster_url] = Proxy.Media(getFanart(poster_url))
									if banner_url not in season.banners:
										season.banners[banner_url] = Proxy.Media(getFanart(banner_url))
									if thumb_url not in episode.thumbs:
										episode.thumbs[thumb_url] = Proxy.Media(getFanart(thumb_url))
									
									showRated = show.get('ShowRated')
									if(showRated.find("TV") >= 0):
										metadata.content_rating = showRated.replace("TV", "TV-")
									
									#Log.Debug('*** callingggggggg: id=%s' % media.id)
									#setWatchedUnwatchedFlag(str(media.seasons[s].episodes[e].id), airing.get('IsWatched'))
									#episode.writers = 
									#episode.directors = 
									#episode.producers = 
									#episode.rating = 
									
									Log.Debug("COMPLETED SETTING EPISODE-LEVEL METADATA FOR SEASON: %s; EPISODE: %s;;;;episode.title=%s;episode.summary=%s;episode.originally_available_at=%s;episode.duration=%s;episode.season=%s;metadata.content_rating=%s;" % (seasonNum, episodeNum, episode.title, episode.summary, episode.originally_available_at, episode.duration, episode.season, metadata.content_rating))
									
									break
