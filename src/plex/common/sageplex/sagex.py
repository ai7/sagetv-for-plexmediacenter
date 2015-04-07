# my module that deals with sagex API calls
#
# python falsy values: None/False/0/''/{}
# function implicit return: None

import os, urllib, json, logging

DEFAULT_CHARSET = 'UTF-8'

def unicodeToStr(obj):
    '''Convert unicode string/array/dict to UTF-8

    @param obj  str/array/dict to be converted
    @return     UTF-8 encoded obj of same type
    '''
    t = obj
    if (t is unicode):
        return obj.encode(DEFAULT_CHARSET)
    elif (t is list):
        for i in range(0, len(obj)):
            obj[i] = unicodeToStr(obj[i])
        return obj
    elif (t is dict):
        for k in obj.keys():
            v = obj[k]
            del obj[k]
            obj[k.encode(DEFAULT_CHARSET)] = unicodeToStr(v)
        return obj
    else:
        return obj # leave numbers and booleans alone

class SageX:
    '''Class that handles talking to a sagex service via HTTP interface'''

    def __init__(self, host='localhost', port='8080',
                 user='sage', password='frey', url=None):
        '''Creates a SageX object

        Takes either a url such as http://usr:pwd@host:port directly,
        or the set of values (host, port, user, password) for which
        the url will be constructed from.

        @param host      hostname or ip of SageTv with sagex running
        @param port      port number
        @param user      username
        @param password  password
        @param url       full url, other parameter is ignored
        '''
        if url:
            if not url.endswith('/'):
                url += '/'
            self._sagex_host = url
        else:
            # http://sage:frey@localhost:8080
            self._sagex_host = ('http://%s:%s@%s:%s/' %
                                (user, password, host, port))

    def _getApiUrl(self, func, params, service, encoder):
        '''Generate the URL we need to make the sagex API call

        @param func     sagex API function name
        @param params   [list] of parameters
        @param service  custom service name, or None
        @param encoder  result encoders: xml, json, and nielm
        @return         url for making the call
        '''
        # first construct the function parameters
        # &1=params[0]&2=params[1]...
        pStr = '';
        i = 1
        for p in params:
            # escape any space in filenames
            pStr += ('&' + str(i)) + '=' + urllib.quote(p)
            i += 1

        # append : to custom service if specified
        if service:
            service += ':'

        # now construct the URL
        # /sagex/api?c=plex:GetMediaFileForName&1=%s&encoder=json
        url = (self._sagex_host +
               ('sagex/api?c=%s%s%s&encoder=%s' %
                (service, func, pStr, encoder)))
        return url;

    def call(self, func, params=[], service='', encoder='json'):
        '''Make a generic sagex API call

        @param func     function to call
        @param params   [list] of parameters
        @param service  custom service name, or None
        @param encoder  result encoders: xml, json, and nielm
        @return         result of call as string
        '''
        if not func:
            logging.error("SageX.call: func is NULL")
            return
        url = self._getApiUrl(func, params, service, encoder);

        # now open the url
        try:
            # logging.info('SageX.call: ' + url)
            input = urllib.urlopen(url)
            fileData = input.read()
        except IOError, e:
            logging.error("SageX.call: failed to open url: " + url)
            logging.error(e)
            return

        # decode json if specified
        if encoder == 'json':
            s1 = json.JSONDecoder().decode(fileData)
        else:
            s1 = fileData;
        # is this needed?
        return unicodeToStr(s1)

    def GetMediaFileForName(self, filename):
        '''Call the GetMediaFileForName API

        Invoke the GetMediaFileForName API and return the value stored
        under "MediaFile" key.

        @param filename  filename to lookup media info
        @return          json[MediaFile] or None
        '''
        s1 = self.call('GetMediaFileForName', [filename], 'plex');
        if s1:
            return s1.get('MediaFile') # None if key not found
            

def main():
    if len(sys.argv) > 1:
        sagex = SageX(url='http://sage:frey@localhost:8080')
        pprint.pprint(sagex.GetMediaFileForName(sys.argv[1]))
    else:
        print 'Usage: <media_file>'

if __name__ == '__main__':
    import sys, pprint
    main()
