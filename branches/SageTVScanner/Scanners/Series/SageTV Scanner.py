#
# Copyright (c) 2010 Plex Development Team. All rights reserved.
#
import re, os, os.path
import Media, VideoFiles, Stack, Utils
from mp4file import mp4file, atomsearch

sage_regex = '(?P<show>.*?)-(?P<episode>.*?)-'
episode_regexps = [
    '(?P<show>.*?)-(?P<episode>.*?)' # Matcher for Sage Recordings (Movie and TV)
  ]
    #'(?P<show>.*?)[sS](?P<season>[0-9]+)[\._ ]*[eE](?P<ep>[0-9]+)([- ]?[Ee+](?P<secondEp>[0-9]+))?',                           # S03E04-E05
    #'(?P<show>.*?)[sS](?P<season>[0-9]{2})[\._\- ]+(?P<ep>[0-9]+)',                                                            # S03-03
    #'(?P<show>.*?)([^0-9]|^)(?P<season>[0-9]{1,2})[Xx](?P<ep>[0-9]+)(-[0-9]+[Xx](?P<secondEp>[0-9]+))?',                       # 3x03
    #'(.*?)[^0-9a-z](?P<season>[0-9]{1,2})(?P<ep>[0-9]{2})([\.\-][0-9]+(?P<secondEp>[0-9]{2})([ \-_\.]|$)[\.\-]?)?([^0-9a-z%]|$)' # .602.    
#  ]

# Look for episodes.
def Scan(path, files, mediaList, subdirs):
  #print "MREID -- Entering SCAN!"
  # Scan for video files.
  VideoFiles.Scan(path, files, mediaList, subdirs)
  
  # Take top two as show/season, but require at least the top one.
  paths = Utils.SplitPath(path)
  #print "MREID - files  = %s" % files
  #print "MREID - paths = %s" % len(paths)
  #print "MREID - paths[0] = %s" % len(paths[0])

  # Run the select regexps we allow at the top level.
  ep_num = 0
  for i in files:
    file = os.path.basename(i)
    #print "MREID - file = %s" % file
    
#    for rx in episode_regexps:
      #print "MREID - inside 2nd for loop"
      #print "MREID - rx = %s" % rx
    match = re.search(sage_regex, file, re.IGNORECASE)
      #print "MREID - match = %s" % match
    if match:
        # Extract data.
      show = match.group('show')
      s_num = 0
      ep_num = ep_num + 1
      ep_name = match.group('episode')
      print "Show = %s" % show
      print "Episode = %s" % ep_name
      tv_show = Media.Episode(show,s_num, ep_num,ep_name, '')
      print "MREID - TVShow = %s" % tv_show
      tv_show.display_offset = 0
      tv_show.parts.append(i)
      mediaList.append(tv_show)
    else:
      print "MREID - NO MATCH!"
          
  # Stack the results.
  Stack.Scan(path, files, mediaList, subdirs)
  
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