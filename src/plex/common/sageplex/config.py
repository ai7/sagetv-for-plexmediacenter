#####################################################################
#
# Author:  Raymond Chi
#
# This file handles sageplex configuration
#
# The JSON configuration file is set via the SAGEPLEX_CFG environment
# variable.
#
# For example:
#   SAGEPLEX_CFG=%LOCALAPPDATA%\\Plex Media Server\\sageplex_cfg.json
#
# don't use logging here because the log location is determined here
#
######################################################################

import os, json

import plexlog  # log wrapper for scanner/agent

##### various defaults *****

# default environment variable that points to config file
DEFAULT_CFG_ENV = 'SAGEPLEX_CFG'

# configuration filename
CFG_FILE = 'sageplex_cfg.json'

# default log file name
LOG_FILE = 'sageplex_scanner.log'

# default PMS data location
LOC_WIN = [ '%LOCALAPPDATA%\\Plex Media Server',
            '%USERPROFILE%\\Local Settings\\Application Data\\Plex Media Server' ]

LOC_MAC = [ '$HOME/Library/Application Support/Plex Media Server' ]

LOC_LIN = [ '$HOME/Library/Application Support/Plex Media Server',
            '/config/Library/Application Support/Plex Media Server' ]

#####

class Config(object):
    '''Class that handles Configuration for SagePlex'''

    def __init__(self, platform, env_var=DEFAULT_CFG_ENV, log=None):
        '''Create a SagePlexConfig object

        Creates a configuration object by either using default or read
        configuration file pointed by SAGEPLEX_CFG environment
        variable

        @param platform  current platform, either python sys.platform
                         or Platform.OS under PMS
        @param env       environment variable to lookup config file
        @param log       PlexLog obj from agent, or None
        '''
        self.data = {}
        self.SAGEX_HOST = None
        self.PLEX_HOST = None
        if log:  # called from agent
            self.log = log
        else:  # called from scanner, use default (console)
            self.log = plexlog.PlexLog()
        # look up environment variable if specified
        cfg = None
        if env_var:  # if env_var is passed in to constructor
            cfg = os.environ.get(env_var)
            if cfg:  # if env variable exist
                # expand env variables in value such as
                # %LOCALAPPDATA%\Plex Media Server\sageplex_cfg.json
                cfg = os.path.expandvars(cfg)
                self.log.info('Config: %s=%s', env_var, cfg)
                if os.path.isdir(cfg):
                    cfg = os.path.join(cfg, CFG_FILE)
                    self.log.info('Config: %s points to directory, adding %s to path',
                                  env_var, CFG_FILE)
            else:
                self.log.info('Config: no env var %s', env_var)
        # lookup location if no env var used
        if not cfg:
            cfg = os.path.join(self.plexDataDir(platform), CFG_FILE)

        if not os.path.isfile(cfg):
            self.log.error('Config: file not found: %s', cfg)
            return
        # now try to open the JSON file and read it
        self.log.info('Config: %s', cfg)
        try:
            if log: # if in agent, use readFile()
                data_file = self.readFile(cfg)
                if not data_file:
                    self.log.error("Config: readfile() failed to return data")
                    return
                self.data = JSON.ObjectFromString(data_file)
            else: # use python open()
                with open(cfg) as data_file:
                    self.data = json.load(data_file)
        except (IOError, ValueError, os.error), e:
            self.log.error("Config: %s: %s", cfg, e)
            return
        # TODO: do some validation of data here

    def plexDataDir(self, platform):
        '''Returns the PMS data directory location

        @param platform  platform from constructor
        @return          path or None
        '''
        # sys.platform: win32 | darwin | linux2
        # Platform.OS:  MacOSX, Windows or Linux
        platform = platform.lower()
        if (platform == 'win32' or platform == 'windows'):
            # for windows, scan multiple dirs
            pLoc = self.checkDirs(LOC_WIN)
        elif (platform == 'darwin' or platform == 'macosx'):
            pLoc = self.checkDirs(LOC_MAC)
        elif 'linux' in platform:
            pLoc = self.checkDirs(LOC_LIN)
        else: # unknown, return home
            pLoc = os.path.expandvars('$HOME')
        return pLoc

    def checkDirs(self, dirList):
        '''Check the list of dirs and return the 1st one that exists

        @param dirList  directory list that may contain env vars
        @param return   1st one that exist, or empty
        '''
        retval = ''
        for p in dirList:
            pe = os.path.expandvars(p)
            if os.path.isdir(pe):
                retval = pe
                break
            else:
                self.log.info("Config: path does not exist: %s", p)
        return retval

    def readFile(self, filename):
        '''Read a file and return its content

        This is used when running under Agent as open() is not
        available for use.

        @param filename  file to read
        @return          file content or None
        '''
        size = os.path.getsize(filename)
        fd = os.open(filename, os.O_RDONLY)
        data = os.read(fd, size)
        return data

    ##### getters

    def getSagexHost(self):
        '''Return a SAGEX_HOST setting or None'''
        if self.SAGEX_HOST: # if cached value exist, return it
            return self.SAGEX_HOST
        sagex = self.data.get('sagex')
        if sagex:
            user = sagex.get('user')
            password = sagex.get('password')
            host = sagex.get('host')
            port = sagex.get('port')
            # http://user:password@host:port/
            self.SAGEX_HOST = ('http://%s:%s@%s:%s/' %
                               (user, password, host, port))
        return self.SAGEX_HOST

    def getPlexHost(self):
        '''Return a PLEX_HOST setting or None'''
        if self.PLEX_HOST: # if cached value exist, return it
            return self.PLEX_HOST
        plex = self.data.get('plex')
        if plex:
            host = plex.get('host')
            port = plex.get('port')
            # http://host:port/
            self.PLEX_HOST = ('http://%s:%s/' % (host, port))
        return self.PLEX_HOST

    def getScannerExt(self):
        '''Return the list of file extensions scanner cares about'''
        scanner = self.data.get('scanner')
        if scanner:
            return scanner.get('ext')

    def getScannerLog(self):
        '''Return the scanner log location'''
        scanner = self.data.get('scanner')
        if scanner:
            log = scanner.get('log')
            if log:
                if '~' in log:
                    return os.path.expanduser(log)
                else:
                    return os.path.expandvars(log)

    def getScannerDebug(self):
        '''Return the scanner debug setting'''
        scanner = self.data.get('scanner')
        if scanner:
            return scanner.get('debug')

    def getAgentLocking(self):
        '''Return the agent locking setting'''
        agent = self.data.get('agent')
        if agent:
            return agent.get('locking')

    def getPlexToken(self):
        '''Returns the PLEX access token, if any'''
        plex = self.data.get('plex')
        if plex:
            return plex.get('token')


######################################################################

# for testing
def main():
    cfg = Config(sys.platform, 'SAGEPLEX_CFG')
    cfg.log.info('SAGEX_HOST: %s', cfg.getSagexHost())
    cfg.log.info('PLEX_HOST: %s', cfg.getPlexHost())
    cfg.log.info('scanner ext: %s', cfg.getScannerExt())
    cfg.log.info('scanner log: %s', cfg.getScannerLog())
    cfg.log.info('agent locking: %s', cfg.getAgentLocking())
    cfg.log.info('plex token: %s', cfg.getPlexToken())

#if __name__ == '__main__':
#    import sys, logging
#    logging.basicConfig(format='%(asctime)s| %(levelname)-8s| %(message)s',
#                        level=logging.DEBUG)
#    main()

# python falsy values: None/False/0/''/{}
# function implicit return: None
