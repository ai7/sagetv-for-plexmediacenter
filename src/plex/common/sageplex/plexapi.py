#####################################################################
#
# Author:  Raymond Chi
#
# Module that handles various operations with PLEX
#
######################################################################

import urllib

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

import plexlog  # log wrapper for scanner/agent

import pdb


######################################################################
# PlexApi class
######################################################################

class PlexApi(object):
    '''Class that implements some PLEX APIs via HTTP interface'''

    def __init__(self, plexHost, log=None):
        '''Creates a PlexApi object

        @param plexHost  url such as http://host:port/
        @param log       plexlog obj from Agent, or None
        '''
        self.appid = 'com.plexapp.plugins.library'
        # setup log
        if log:  # called from agent
            self.log = log
            self.isAgent = True
        else:  # called from scanner, use default (console)
            self.log = plexlog.PlexLog()
            self.isAgent = False
        # set PLEX_HOST, remove ending / if any
        if plexHost:
            if plexHost[-1] == '/':       # if ends with /
                plexHost = plexHost[:-1]  # remove ending /
            self.PLEX_HOST = plexHost
        else:
            self.PLEX_HOST = ''
            self.log.error('PlexApi: plexHost not specified!!')

    def openUrl(self, url, xml=False, log=True):
        '''Open the url and get the data returned

        @param url  URL to open
        @param xml  whether to return data as XML object
        @param log  whether to write debug log entry
        @return     data from server or None
        '''
        result = None
        try:
            if log:
                self.log.debug('openUrl: %s', url)
            # we can't use the framework's HTTPRequest() or
            # JSON.ObjectFromURL() because it apparently doesn't know
            # how to deal with url that have user/password
            input = urllib.urlopen(url)
            result = input.read()
            if result and xml:
                result = ET.fromstring(result)
        except IOError, e:
            self.log.error("openUrl: failed on: %s: %s", url, str(e))
            result = None
        except ET.ParseError, e:
            self.log.error("openUrl: XML parse failed: %s", str(e))
            result = None
        finally:
            pass

        return result

    def getApiUrl(self, action, values):
        '''Generate the URL we need to make the PLEX API call

        @param action   PLEX action name
        @param values   [list] of key/value parameters for action
        @return         url for making the PLEX API call
        '''
        # first construct the k1=v1&k2=v2 ...
        pstr = '';
        for (k, v) in values:
            if pstr:
                pstr += '&'
            pstr += str(k) + '=' + urllib.quote(str(v))

        # now construct the URL such as
        # /:/scrobble?key=12&identifier=com.plexapp.plugins.library
        url = (self.PLEX_HOST +
               ('/:/%s?%s' % (action, pstr)))
        return url;

    # :/scrobble?key=12&identifier=com.plexapp.plugins.library
    def setWatched(self, id, isWatched):
        '''Set the watched/not-watched flag on media in PLEX

        @param id         plex media id
        @param isWatched  true/false
        '''
        url = self.getApiUrl('scrobble' if isWatched else 'unscrobble',
                             [ ('key', id),
                               ('identifier', self.appid) ])
        return self.openUrl(url)

    # :/progress?key=2288&identifier=com.plexapp.plugins.library&time=77357
    def setProgress(self, id, time):
        '''Set progress on a show

        @param id    plex media id
        @param time  progress time in ms
        '''
        url = self.getApiUrl('progress',
                             [ ('key', id),
                               ('identifier', self.appid),
                               ('time', time) ])
        return self.openUrl(url)

    def listSections(self, byName=False):
        '''List the library sections

        @param byName  whether to index return result by name
        @return        dict of sections by id with attr id/title/type
        '''
        url = ('%s%s' % (self.PLEX_HOST, '/library/sections'))
        ans = self.openUrl(url, xml=True)
        if ans:
            result = {}
            for e1 in ans:
                x = {}
                x['id'] = e1.get('key')
                x['title'] = e1.get('title')
                x['type'] = e1.get('type')
                if byName:
                    result[x['title']] = x
                else:
                    result[x['id']] = x
            return result

    def joinPath(self, path, newPath):
        '''Form a new path from existing and a new path component

        If newPath begins with /, use newPath, otherwise add newPath
        to oldPath (path/newPath)

        @param path     the current path
        @param newPath  the new path, such as "25", or "/data"
        @return         the resulting joined path
        '''
        # if new path starts with /, return new path
        if newPath[0] == '/':
            return newPath
        # else join the 2 path together
        if path[-1] == '/':
            return path + newPath
        else:
            return path + '/' + newPath

    def walkPlex(self, path, key, leafCb, level=1):
        '''A recursive function to walk the PLEX library tree

        A callback function can be specified to do something useful at
        each leaf node, ie, a node that contains video elements.

        @param path    path to walk, ie, /library/sections
        @param key     the key that lead to this path
        @param leafCb  callback function when at leaf node
        @param level   internal, recursion depth
        '''
        # just in case, bail out if recursed too deep
        if level > 7:
            self.log.debug("recursion limit reached [%d]: %s",
                           level, path)
            return
        # issue the query and get result
        url = ('%s%s' % (self.PLEX_HOST, path))
        ans = self.openUrl(url, xml=True, log=False)
        # sanity check result
        TAG_TYPE = 'MediaContainer'
        if not ans:
            self.log.error("walkPlex: url returned no data")
            return
        if ans.tag != TAG_TYPE:
            self.log.error("walkPlex: expecting <%s> but got: <%s>",
                           TAG_TYPE, ans.tag)
            return
        val = ans.get('size')
        if val and int(val) < 1:
            self.log.warning("walkPlex: <%s> size=%s, skipping",
                             TAG_TYPE, ans.get('size'))
            return
        # now loop through the child elements
        for e1 in ans:
            title = e1.attrib['title']
            childKey = e1.attrib['key']
            # print child element information
            self.log.debug("%s%s (%s)", '  ' * level, title, childKey)
            # if child is <Video>, we are done. if child key is the
            # same as the current key, leaf node, we are also done.
            if e1.tag == 'Video' or key == childKey:
                if leafCb:
                    leafCb(e1, self.log)
                continue
            # skipping all episodes, do iteration in season X
            if title == 'All episodes':
                self.log.debug("%sSkipping %s", '  ' * level, title)
                continue
            # append key to path, and recurse
            newPath = self.joinPath(path, childKey)
            self.walkPlex(newPath, childKey, leafCb, level+1)


######################################################################

# for testing

def main():
    if len(sys.argv) < 2:
        print 'Usage: <plex_media_id>'
        return
    papi = PlexApi('http://localhost:32400/')
    print papi.listSections()

#if __name__ == '__main__':
#    import sys, logging, pprint
#    logging.basicConfig(format='%(asctime)s| %(levelname)-8s| %(message)s',
#                        level=logging.DEBUG)
#    main()

# useful stuff
# python falsy values: None/False/0/''/{}
# function implicit return: None
