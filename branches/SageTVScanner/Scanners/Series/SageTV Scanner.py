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
import re, os, os.path
import Media, VideoFiles, Stack, Utils
from mp4file import mp4file, atomsearch

#  
#  regular expression used to find sagetv recordings in the specified directory
#  SageTV files are formated as show-episode-randomnumbers.txt and can in some cases include SxxExx
#  information.
#-------------------
sage_regex = '(?P<show>.*?)-*?-?(?P<episode>.*?)-'

# Look for episodes.
def Scan(path, files, mediaList, subdirs):

  # Scan for video files.
  VideoFiles.Scan(path, files, mediaList, subdirs)
  
  paths = Utils.SplitPath(path)
  
  # default episode number to 0.  We wont' grab episode number or season number in this scanner
  # that info will be obtained in SageTVBMTAgent.  In order to send a valid object we must default
  # season and episode to 0,0.  We are setting episode number outside of the loop used to interate over
  # files in order to increment the episodes scanned from 1 - x
  #--------------
  ep_num = 0 
  
  # loop used to interate over all files found in VideoFiles.Scan above
  for i in files:
    file = os.path.basename(i)
    match = re.search(sage_regex, file, re.IGNORECASE)
    #print "File name = %s" % file
    
    # If we find a match using the regex above, extract data, create media object, and append to results
    if match:
      # Extract data.
      show = match.group('show')
      s_num = 0
      ep_num = ep_num + 1
      ep_name = match.group('episode')
      
      #print "Show = %s" % show
      #print "Episode = %s" % ep_name
      
      tv_show = Media.Episode(show,s_num, ep_num,ep_name, '')
      
      #print "MREID - TVShow = %s" % tv_show
      
      tv_show.display_offset = 0
      tv_show.parts.append(i)
      mediaList.append(tv_show)
    else:
      print "**** No Match found for file %s" % file
          
  # Stack the results.
  Stack.Scan(path, files, mediaList, subdirs)
  
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