#    Author: PiX(64) - Reid, Michael
# 
#    Source: This scanner was built using code found in Plex Media Scanner.py.
#    Thank you to the plex development team for their help and great starting point.
#
#    Purpose:  The purpose of SageTV Movie Scanner.py is to provide a means for Plex Media Center to scan
#    SageTV Recording directories.  This scanner will find ALL sage recordings including Movies recorded by sage
#    and movies sage knows about.  This file used in conjuction with SageTV BMT Scanner (BMTAgent.bundle) will allow 
#    users to include
#    sage tv recordings and all BMT scraped metadata into their plex media server setup.
#-----------------------------------------
import re, os, os.path, urllib, simplejson as json
import Media, VideoFiles, Stack, Utils
from mp4file import mp4file, atomsearch
#from datetime import date

DEFAULT_CHARSET = 'UTF-8'

# Enter ip address and port http://x.x.x.x:port
# or if you server requires user/pass enter http://user:pass@x.x.x.x:port
SAGEX_HOST = 'http://192.168.1.110:8500'

# Look for episodes.
def Scan(path, files, mediaList, subdirs):
  # Scan for video files.
  VideoFiles.Scan(path, files, mediaList, subdirs)
  
  paths = Utils.SplitPath(path)
  
  #Try and read properties file before doing any scanning
  #if( not readPropertiesFromPropertiesFile()):
  #  print "****UNABLE TO READ BMTAGENT.PROPERTIES FILE... aborting search"
  #else: 
  #  print "Successfully read properties file"
  
  # loop used to interate over all files found in VideoFiles.Scan above
  for i in files:
    file = os.path.basename(i)
    (file, ext) = os.path.splitext(file)
    print "*** Found File name = %s%s, Start looking for metadata" % (file,ext)
    #if the extension is in our list of acceptable sagetv file extensions, then process
    if ext.lower() in ['.mpg', '.avi', '.mkv', '.mp4', '.ts']:
      mf = getMediaFileForFilePath(urllib.quote(file + ext))
      if(mf): # this would only return false if there is a file on the Plex import directory but that file is not yet in Sage's DB
        airing = mf.get('Airing')
        showMF = airing.get('Show')
        if (showMF):
          category = showMF.get('ShowCategoriesString')
          showTitle = showMF.get('ShowTitle').encode('UTF-8')
          showYear = showMF.get('ShowYear').encode('UTF-8')
          if(showYear == None or showYear == ""):
            showYear = ''
          if(category.find("Movie")>=0 or category.find("Movies")>=0 or category.find("Film")>=0):
            movie = Media.Movie(showTitle, showYear)
            movie.source = VideoFiles.RetrieveSource(file)
            movie.parts.append(i)
            mediaList.append(movie)
            # Stack the results.
            Stack.Scan(path, files, mediaList, subdirs)
            print "****** Current file (%s%s) successfully added to stack!" % (file,ext)
          else:
            print "****** Current file (%s%s) is a TVShow" % (file,ext)
        else:
          print "****** Current file (%s%s) did not return a valid MEdiaFile Object from BMT" % (file,ext)
      else:
        print "****** Current file (%s%s) was not found in BMT!)" % (file,ext)
    else:
      print "******NO MATCH FOUND BY SCANNER!"

#
# Code user for Sagex api calls
#
#----------
def getMediaFileForFilePath(filename):
	url = SAGEX_HOST + '/sagex/api?c=plex:GetMediaFileForName&1=%s&encoder=json' % filename
	return executeSagexAPICall(url, 'MediaFile')

def executeSagexAPICall(url, resultToGet):
	#print '*** sagex request URL: %s' % url
	try:
		input = urllib.urlopen(url)
	except IOError, i:
		print "ERROR in executeSagexAPICall: Unable to connect to SageTV server"
		return None
	fileData = input.read()
	#print "MREID - fileData = %s" % fileData 
	resp = unicodeToStr(json.JSONDecoder().decode(fileData))

	#print '*** sagex API call "%s" [args: %s] succeeded!' % (url, resp)
	
	objKeys = resp.keys()
	numKeys = len(objKeys)
	if(numKeys == 1):
		return resp.get(resultToGet)
	else:
		return None

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