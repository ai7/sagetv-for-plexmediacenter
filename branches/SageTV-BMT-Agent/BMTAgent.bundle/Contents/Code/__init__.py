# PiX64 (mreid) initial code
#
# lehibri (bschneider)
#  continued development
#
import re, time, unicodedata, hashlib, types, urllib, simplejson as json
from time import strftime
from datetime import date

SAGEX_HOST = 'http://x.x.x.x:port'

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
	return executeSagexAPICall(url, 'Result')
  
class BMTAgent(Agent.TV_Shows):
  name = 'SageTV BMT Agent'
  languages = [Locale.Language.English]
  primary_provider = True
  #fallback_agent = False
  #accepts_from = 'com.plexapp.agents.thetvdb'
  #contributes_to = ['com.plexapp.agents.thetvdb']
		
  def search(self, results, media, lang, manual):
	#filename = media.items[0].parts[0].file.decode('utf-8')
	quotedFilename = media.filename
	Log.Debug('***quotedFilename=%s' % quotedFilename)
	unquotedFilename = urllib.unquote(quotedFilename)
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

	episode.title = show.get('ShowEpisode')
	if(episode.title == ""):
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
