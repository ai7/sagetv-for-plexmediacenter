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
	return resp
  
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
			cwd = cwd.replace("Plug-in Support\\Data\\com.plexapp.agents.bmtagentmovies", "Plug-ins\\BMTAgentMovies.bundle\\Contents\\Code\\")
		elif(len(cwd) == 1): #for some reason on Macs, CWD returns just a forward slash /
			cwd = "~/Library/Application Support/Plex Media Server/Plug-ins/BMTAgentMovies.bundle/Contents/Code/"
		elif(cwd.find("/") >=0): #forward slashes are typically from non-windows machines
			cwd = cwd.replace("Plug-in Support/Data/com.plexapp.agents.bmtagentmovies", "Plug-ins/BMTAgentMovies.bundle/Contents/Code/")

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

class BMTAgent(Agent.Movies):
  name = 'SageTV BMT Agent (Movies)'
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
	Log.Debug('****media.id=%s; media.filename=%s' % (str(media.id), quotedFilepathAndName))
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
		if(category.find("Movie")>=0 or category.find("Movies")>=0 or category.find("Film")>=0):
			startTime = float(show.get('OriginalAiringDate') // 1000)
			airDate = date.fromtimestamp(startTime)
			results.Append(MetadataSearchResult(id=str(mf.get('MediaFileID')), name=unquotedFilepathAndName, score=100, lang=lang, year=airDate.year))
		else:
			Log.Debug('***Movies/Movies/Film NOT found, ignoring and will not call update; categorylist=%s' % category)

  def update(self, metadata, media, lang, force):
	Log.Debug('***UPDATE CALLEDDDDDDDDDDDDDDDDDDDDDDDD')
	mediaFileID = str(metadata.id)
	mf = getMediaFileForID(mediaFileID)
	airing = mf.get('Airing')
	show = airing.get('Show')
	
	#Set the Movies's metadata
	metadata.title = show.get('ShowTitle')
	metadata.title_sort = metadata.title
	metadata.summary = show.get('ShowDescription')
	#metadata.tagline = show.get('ShowDescription')
	metadata.duration = mf.get('FileDuration')
	series = getShowSeriesInfo(show.get('ShowExternalID'))
	if(series):
		seriesPremiere = series.get('SeriesPremiereDate')
		Log.Debug('***seriesPremiere=%s' % seriesPremiere)
		airDate = datetime.datetime.strptime(seriesPremiere, '%Y-%m-%d')
		Log.Debug('***airDate=%s' % str(airDate))
		metadata.originally_available_at = airDate
		metadata.studio = series.get('SeriesNetwork')	
	
	showRated = show.get('ShowRated')
	if(showRated.find("PG13") >= 0):
		metadata.content_rating = "PG-13"

	cats = show.get('ShowCategoriesList')
	metadata.genres.clear()
	for cat in cats:
		if(cat != "Movies" and cat != "Movie" and cat != "Film"):
			Log.Debug("cat=%s" % cat)
			metadata.genres.add(cat)
	
	#metadata.posters
	background_url = SAGEX_HOST + '/sagex/media/background/%s' % mediaFileID
	poster_url = SAGEX_HOST + '/sagex/media/poster/%s' % mediaFileID

	metadata.art[background_url] = Proxy.Media(getFanart(background_url))
	metadata.posters[poster_url] = Proxy.Media(getFanart(poster_url))
	
	# If we haven't added this poster.
	#if poster_url not in metadata.posters:
		# Add the poster.
		#metadata.posters[poster_url] = Proxy.Media(data)

	roles = show.get('RolesInShow')
	stars = show.get('PeopleListInShow')
	metadata.directors.clear()
	i = 0
	while i < len(roles):
		if(roles[i] == "Director"):
			Log.Debug("Director found: roles[%d]=%s" % (i, stars[i]))
			metadata.directors.add(stars[i])
		i = i+1
	
	Log.Debug("Metadata that was set includes: metadata.title=%s;metadata.summary=%s;metadata.originally_available_at=%s;metadata.duration=%s;metadata.content_rating=%s;" % (metadata.title, metadata.summary, metadata.originally_available_at, metadata.duration, metadata.content_rating))

