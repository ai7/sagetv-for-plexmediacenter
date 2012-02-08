#    Author: PiX(64) - Reid, Michael
# 
#    Source: This scanner was built using code found in Plex Media Scanner.py.
#    Thank you to the plex development team for their help and great starting point.
#
#    Purpose:  The purpose of SageTV Scanner.py is to provide a means for Plex Media Center to scan
#    SageTV Recording directories.  This scanner will find ALL sage recordings including Movies and TV
#    This file used in conjuction with SageTV BMT Scanner (BMTAgent.bundle) will allow users to include
#    sage tv recordings and all BMT scraped metadata into their plex media server setup.
#-----------------------------------------
import re, os, os.path, urllib, simplejson as json
import Media, VideoFiles, Stack, Utils
from mp4file import mp4file, atomsearch
#from datetime import date

DEFAULT_CHARSET = 'utf-8'

# Enter ip address and port http://x.x.x.x:port
# or if you server requires user/pass enter http://user:pass@x.x.x.x:port
SAGEX_HOST = 'http://192.168.1.110:8500'

#  
#  regular expression used to find sagetv recordings in the specified directory
#  SageTV files are formated as show-episode-randomnumbers.txt and can in some cases include SxxExx
#  information.
#-------------------
#sage_regex = '(?P<show>.*?)-?(([sS])(?P<s_num>[0-9]+)[eE](?P<ep_num>[0-9]+))?-(?P<episode>.*?)-'
#sage_regex = '(?P<show>.*?)-(?P<episode>.*?)-'
#
# The above code is no longer needed, but leaving for reference for now
#---------------------------

#
# Code user for Sagex api calls
#
#----------
def getMediaFileForFilePath(filename):
	url = SAGEX_HOST + '/sagex/api?c=plex:GetMediaFileForName&1=%s&encoder=json' % filename
	#url = 'http://192.168.1.110:8500/sagex/api?c=plex:GetMediaFileForName&1=%s&encoder=json' % filename
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
    #print "File name = %s" % file
    #print "File ext = %s" % ext
    #match = re.search(sage_regex, file, re.IGNORECASE)
    print "*** Found File name = %s%s, Starting to look for metedata." % (file,ext)
    # If we find a match using the regex above, extract data, create media object, and append to results
    #if match:
    #if the extension is in our list of acceptable sagetv file extensions, then process
    if ext.lower() in ['.mpg', '.avi', '.mkv', '.mp4', '.ts']:
      mf = getMediaFileForFilePath(urllib.quote(file + ext))
      if(mf): # this would only return false if there is a file on the Plex import directory but that file is not yet in Sage's DB
        airing = mf.get('Airing')
        showMF = airing.get('Show')
        if (showMF):
          category = showMF.get('ShowCategoriesString')
          showTitle = showMF.get('ShowTitle').encode('UTF-8')
          episodeTitle = showMF.get('ShowEpisode').encode('UTF-8')
          if( episodeTitle == None or episodeTitle == ""):
            episodeTitle = showTitle
      
          showYear = showMF.get('ShowYear').encode('UTF-8')
          if(showYear == None or showYear == ""):
            showYear = ''
	      # Retrieve show original air date, and grab the year out of it for storage
          #startTime = float(showMF.get('OriginalAiringDate') // 1000)
          #showDate = date.fromtimestamp(startTime)
          #showYear = showDate.year
		
          s_num = str(showMF.get('ShowSeasonNumber')) # must convert to string or else Plex throws a serialization exception
          ep_num = str(showMF.get('ShowEpisodeNumber')) # must convert to string or else Plex throws a serialization exception
          #print "Sage show = %s" % s_num
          #print "Sage Episode = %s" % ep_num          
          #print "Sage Show name = %s" % showTitle
          #print "Sage Episode name = %s" % episodeTitle
      
          if(s_num == None or s_num == ""): # if there is no season or episode number, default it to 0 so that Plex can still pull it in
            s_num = 0
          if(ep_num == None or ep_num == ""):
            ep_num = 0
        
          if(category.find("Movie")<0 and category.find("Movies")<0 and category.find("Film")<0):
            tv_show = Media.Episode(showTitle,s_num, ep_num,episodeTitle, showYear)
		    #print "MREID - TVShow = %s" % tv_show
            tv_show.display_offset = 0
            tv_show.parts.append(i)
            mediaList.append(tv_show)
            # Stack the results.
            Stack.Scan(path, files, mediaList, subdirs)
            print "****** Current file (%s%s) successfully added to stack!" % (file,ext)
          else:
            print "****** Current file (%s%s) is a Movie or Film! Removing from scanner" % (file,ext)
        else:
          print "****** Current file (%s%s) did not have a proper mediafile object returned from SageTV BMT" % (file,ext)
      else:
        print "****** Current file (%s%s) was not found int BMT!" % (file,ext)
    else:
      print "*** NO MATCH FOUND BY SCANNER!"
      
#
#    The following code was present in the original code Plex Media Scanner.py
#    It was left as is as I am not 100% sure of its use.
#----------------------------
def find_data(atom, name):
  child = atomsearch.find_path(atom, name)
  data_atom = child.find('data')
  if data_atom and 'data' in data_atom.attrs:
    return data_atom.attrs['data']

import sys
    
if __name__ == '__main__':
  print "Hello, world!"
  path = sys.argv[1]
  files = [os.path.join(path, file) for file in os.listdir(path)]
  media = []
  Scan(path[1:], files, media, [])
  print "Media:", media