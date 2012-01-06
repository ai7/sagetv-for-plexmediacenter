import re, time, unicodedata, hashlib, types, urllib, os, simplejson as json
from time import strftime
from datetime import date

SAGEX_HOST = ""
UNC_MAPPINGS = ""

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
  
def getSageTVMediafileObject(filename):
	url = SAGEX_HOST + '/sagex/api?c=GetMediaFileForFilePath&1=%s&encoder=json' % urllib.pathname2url(filename) 
	return executeSagexAPICall(url, 'MediaFile')
  
def isFileInSageTVDB(filename):
	url = SAGEX_HOST + '/sagex/api?c=IsFilePath&1=%s&encoder=json' % urllib.pathname2url(filename) 
	return bool(executeSagexAPICall(url, 'Result'))
  
def readPropertiesFromPropertiesFile():
	global SAGEX_HOST, UNC_MAPPINGS
	cwd = os.getcwd()
	Log.Debug('***cwdddddddddddd=%s' % cwd)
	cwd = cwd.replace("\\\\?\\", "")
	cwd = cwd.replace("Plug-in Support\\Data\\com.plexapp.agents.bmtagent", "Plug-ins\\BMTAgent.bundle\\Contents\\Code\\")
	propertiesFilePath = cwd + "BMTAgent.properties"
	Log.Debug('***propertiesFilePath=%s' % propertiesFilePath)
	if(os.path.isfile(propertiesFilePath)):
		f = os.open(propertiesFilePath, os.O_RDONLY)
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
		elif(keyValues[0] == "UNC_MAPPINGS"):
			UNC_MAPPINGS = keyValues[1]
	
	os.close(f)
  
class BMTAgent(Agent.TV_Shows):
  name = 'SageTV BMT Agent'
  languages = [Locale.Language.English]
  primary_provider = True
  #fallback_agent = False
  #accepts_from = 'com.plexapp.agents.thetvdb'
  #contributes_to = ['com.plexapp.agents.thetvdb']
		
  def search(self, results, media, lang, manual):
	#filename = media.items[0].parts[0].file.decode('utf-8')
	readPropertiesFromPropertiesFile()
	
	quotedFilename = media.filename
	if(UNC_MAPPINGS == ""):
		unquotedFilename = urllib.unquote(quotedFilename)
	else:
		#Map the path from Plex (which only does drive letters) to what could be a network share location that Sage uses
		maps = UNC_MAPPINGS.split(';')
		for mapValues in maps:
			map = mapValues.split(',')
			unquotedFilename = urllib.unquote(quotedFilename)
			unquotedFilename = unquotedFilename.replace(map[0],map[1])
			quotedFilename = urllib.quote(unquotedFilename)
	
	Log.Debug('***quotedFilename=%s' % quotedFilename)
	Log.Debug('***unquotedFilename=%s' % unquotedFilename)
	fileExists = isFileInSageTVDB(unquotedFilename)
	
	if(fileExists):
		mf = getSageTVMediafileObject(unquotedFilename)
		if(mf): # this would only return false if there is a file on the Plex import directory but that file is not yet in Sage's DB
			airing = mf.get('Airing')
			show = airing.get('Show')
			
			# Check if the Sage recording is a movie or film; if it is, ignore it (workaround for user is to move movies out to a separate import directory that Plex can read an import as Movie content vs. TV Show content
			category = show.get('ShowCategoriesString')
			if(category.find("Movie")<0 and category.find("Movies")<0 and category.find("Film")<0):
				startTime = float(show.get('OriginalAiringDate') // 1000)
				airDate = date.fromtimestamp(startTime)
				results.Append(MetadataSearchResult(id=quotedFilename, name=unquotedFilename, score=100, lang=lang, year=airDate.year))
			else:
				Log.Debug('***Movies/Movies/Film found, ignoring and will not call update; categorylist=%s' % category)

  def update(self, metadata, media, lang, force):
	Log.Debug('***UPDATE CALLEDDDDDDDDDDDDDDDDDDDDDDDD')
	#filename = media.items[0].parts[0].file.decode('utf-8')
	filename = urllib.unquote(metadata.id)
	mf = getSageTVMediafileObject(filename)
	airing = mf.get('Airing')
	show = airing.get('Show')
	
	#Set the Show's metadata
	metadata.title = show.get('ShowTitle')
	metadata.title_sort = metadata.title
	metadata.summary = getShowSeriesInfo(show.get('ShowExternalID'))
	cats = show.get('ShowCategoriesList')
	i = 0
	for cat in cats:
		metadata.genres[i] = cat
		Log.Debug("metadata.genres[%d]=%s" % (i, cat))
		i = i+1
	
	# Set the Episode's metadata
	s = str(show.get('ShowSeasonNumber')) # must convert to string or else Plex throws a serialization exception
	e = str(show.get('ShowEpisodeNumber')) # must convert to string or else Plex throws a serialization exception
	if(s == ""): # if there is no season or episode number, default it to 0 so that Plex can still pull it in
		s = "0"
		e = "0"
	Log.Debug("UPDATING METADATA FOR SEASON: %s; EPISODE: %s" % (s, e))
	episode = metadata.seasons[s].episodes[e]

	startTime = float(show.get('OriginalAiringDate') // 1000)
	airDate = date.fromtimestamp(startTime)

	if(show.get('ShowEpisode') == ""):
		episode.title = show.get('ShowEpisode')
	else:
		episode.title = show.get('ShowTitle')
	episode.summary = show.get('ShowDescription')
	episode.originally_available_at = airDate
	episode.duration = mf.get('FileDuration')
	episode.season = show.get('ShowSeasonNumber')
	episode.guest_stars = show.get('PeopleListInShow')
	#episode.writers = 
	#episode.directors = 
	#episode.producers = 
	#episode.rating = 
	#episode.genres = show.get('ShowCategoriesString')
	
	Log.Debug("Metadata that was set includes: episode.title=%s;episode.summary=%s;episode.originally_available_at=%s;episode.duration=%s;episode.season=%s;" % (episode.title, episode.summary, episode.originally_available_at, episode.duration, episode.season))

