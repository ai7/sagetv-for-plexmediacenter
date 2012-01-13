import re, time, unicodedata, hashlib, types, urllib, os, simplejson as json
from time import strftime
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
	Log.Debug('*** sagex request URL: %s' % url)
	try:
		input = urllib.urlopen(url)
	except IOError, i:
		Log.Debug("ERROR in executeSagexAPICall: Unable to connect to SageTV server")
		return None
	fileData = input.read()
	resp = unicodeToStr(json.JSONDecoder().decode(fileData))

	Log.Debug('*** sagex API call "%s" [args: %s] succeeded!' % (url, resp))
	
	objKeys = resp.keys()
	numKeys = len(objKeys)
	if(numKeys == 1):
		return resp.get(resultToGet)
	else:
		return None
  
def getShowSeriesInfo(showID):
	url = SAGEX_HOST + '/sagex/api?c=GetShowSeriesInfo&1=show:%s&encoder=json' % showID
	resp = executeSagexAPICall(url, 'SeriesInfo')
	if(resp):
		return resp.get('SeriesDescription')
	else:
		return None
  
def getMediaFileForID(mediaFileID):
	url = SAGEX_HOST + '/sagex/api?c=GetMediaFileForID&1=%s&encoder=json' % mediaFileID
	return executeSagexAPICall(url, 'MediaFile')
  
def getMediaFileForFilePath(filename):
	#url = SAGEX_HOST + '/sagex/api?c=GetMediaFileForFilePath&1=%s&encoder=json' % filename
	url = SAGEX_HOST + '/sagex/api?c=plex:GetMediaFileForName&1=%s&encoder=json' % filename
	return executeSagexAPICall(url, 'MediaFile')
  
def readPropertiesFromPropertiesFile():
	global SAGEX_HOST, PLEX_HOST
	try:
		cwd = os.getcwd()
		Log.Debug('***cwdddddddddddd=%s' % cwd)
		if(cwd.find("\\") >=0): #backslashes are typically from windows machines
			cwd = cwd.replace("\\\\?\\", "")
			cwd = cwd.replace("Plug-in Support\\Data\\com.plexapp.agents.bmtagent", "Plug-ins\\BMTAgent.bundle\\Contents\\Code\\")
		elif(cwd.find("/") >=0): #forward slashes are typically from non-windows machines
			cwd = cwd.replace("Plug-in Support/Data/com.plexapp.agents.bmtagent", "Plug-ins/BMTAgent.bundle/Contents/Code/")

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
		Log.Debug("***getFanart: Attempting to fetch fanart from the following url:%s" % url)
		response = urllib.urlopen(url)
		fileData = response.read()
		Log.Debug("***getFanart: Successfully read fanart from the following url:%s" % url)
	except IOError, i:
		Log.Debug("ERROR in getFanart: Unable to download fanart at the following URL: %s" % url)
		return None
	return fileData

class BMTAgent(Agent.TV_Shows):
  name = 'SageTV BMT Agent'
  languages = [Locale.Language.English]
  primary_provider = True
  accepts_from = None
  #fallback_agent = False
  #accepts_from = 'com.plexapp.agents.thetvdb'
  #contributes_to = ['com.plexapp.agents.thetvdb']
		
  def search(self, results, media, lang, manual):
	#filename = media.items[0].parts[0].file.decode('utf-8')
	if(not readPropertiesFromPropertiesFile()):
		Log.Debug("****UNABLE TO READ BMTAGENT.PROPERTIES FILE... aborting search")
	
	quotedFilepathAndName = media.filename
	unquotedFilepathAndName = urllib.unquote(quotedFilepathAndName)
	# Pull out just the filename to use
	if(unquotedFilepathAndName.find("\\")<0):
		unquotedFilename = unquotedFilepathAndName[unquotedFilepathAndName.rfind("//")+1:len(unquotedFilepathAndName)]
	else:
		unquotedFilename = unquotedFilepathAndName[unquotedFilepathAndName.rfind("\\")+1:len(unquotedFilepathAndName)]
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
			results.Append(MetadataSearchResult(id=str(mf.get('MediaFileID')), name=unquotedFilepathAndName, score=100, lang=lang, year=airDate.year))
		else:
			Log.Debug('***Movies/Movies/Film found, ignoring and will not call update; categorylist=%s' % category)

  def update(self, metadata, media, lang, force):
	Log.Debug('***UPDATE CALLEDDDDDDDDDDDDDDDDDDDDDDDD')
	mediaFileID = str(metadata.id)
	mf = getMediaFileForID(mediaFileID)
	airing = mf.get('Airing')
	show = airing.get('Show')
	
	#Set the Show's metadata
	metadata.title = show.get('ShowTitle')
	metadata.title_sort = metadata.title
	metadata.summary = getShowSeriesInfo(show.get('ShowExternalID'))
	metadata.content_rating = show.get('ShowRated')
	cats = show.get('ShowCategoriesList')
	metadata.genres.clear()
	for cat in cats:
		Log.Debug("cat=%s" % cat)
		metadata.genres.add(cat)
	
	#metadata.posters
	background_url = SAGEX_HOST + '/sagex/media/background/%s' % mediaFileID
	poster_url = SAGEX_HOST + '/sagex/media/poster/%s' % mediaFileID
	banner_url = SAGEX_HOST + '/sagex/media/banner/%s' % mediaFileID

	metadata.art[background_url] = Proxy.Media(getFanart(background_url))
	metadata.posters[poster_url] = Proxy.Media(getFanart(poster_url))
	metadata.banners[banner_url] = Proxy.Media(getFanart(banner_url))
	
	# If we haven't added this poster.
	#if poster_url not in metadata.posters:
		# Add the poster.
		#metadata.posters[poster_url] = Proxy.Media(data)

	# Set the Episode's metadata
	s = str(show.get('ShowSeasonNumber')) # must convert to string or else Plex throws a serialization exception
	e = str(show.get('ShowEpisodeNumber')) # must convert to string or else Plex throws a serialization exception
	if(s == ""): # if there is no season or episode number, default it to 0 so that Plex can still pull it in
		s = "0"
		e = "0"
	Log.Debug("UPDATING METADATA FOR SEASON: %s; EPISODE: %s" % (s, e))
	season = metadata.seasons[s]
	episode = season.episodes[e]

	startTime = float(show.get('OriginalAiringDate') // 1000)
	airDate = date.fromtimestamp(startTime)

	if(show.get('ShowEpisode') == ""):
		episode.title = show.get('ShowTitle')
	else:
		episode.title = show.get('ShowEpisode')
	episode.summary = show.get('ShowDescription')
	episode.originally_available_at = airDate
	episode.duration = mf.get('FileDuration')
	episode.season = int(s)
	episode.guest_stars = show.get('PeopleListInShow')
	episode.show = show.get('ShowTitle')
	
	#season.posters
	#season.banners
	season.posters[poster_url] = Proxy.Media(getFanart(poster_url))
	season.banners[banner_url] = Proxy.Media(getFanart(banner_url))

	thumb_url = SAGEX_HOST + '/sagex/media/thumbnail/%s' % mediaFileID
	episode.thumbs[thumb_url] = Proxy.Media(getFanart(thumb_url))
	
	#Log.Debug('*** callingggggggg: id=%s' % media.id)
	#setWatchedUnwatchedFlag(str(media.seasons[s].episodes[e].id), airing.get('IsWatched'))
	#episode.writers = 
	#episode.directors = 
	#episode.producers = 
	#episode.rating = 
	
	Log.Debug("Metadata that was set includes: episode.title=%s;episode.summary=%s;episode.originally_available_at=%s;episode.duration=%s;episode.season=%s;episode.show=%s;metadata.content_rating=%s;" % (episode.title, episode.summary, episode.originally_available_at, episode.duration, episode.season, episode.show, metadata.content_rating))

