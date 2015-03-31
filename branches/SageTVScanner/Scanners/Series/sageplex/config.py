# This file handles sageplex configuration
#
# The JSON configuration file is set via the SAGEPLEX_CFG environment
# variable. For example:
#
# SAGEPLEX_CFG=%LOCALAPPDATA%\\Plex Media Server\\sageplex_cfg.json
#
# can't use logging here because the log location is set here

import os, json


class Config:
    '''Class that handles Configuration for SagePlex'''

    # default values
    _data = {
        "sagex": {
            "host": "localhost",
            "port": 8080,
            "user": "sage",
            "password": "frey"
        },
        "scan_log": "%LOCALAPPDATA%\\Plex Media Server\\Logs\\sageplex_scanner.log"
    }
    
    def __init__(self, env_var='SAGEPLEX_CFG'):
        '''Create a SagePlexConfig object

        Creates a configuration object by either using default or read
        configuration file pointed by SAGEPLEX_CFG environment
        variable

        @param env  environment variable for config file location
        '''
        if not env_var:  # done if no env var passed
            return
        
        cfg = os.environ.get(env_var)
        if not cfg:
            return

        # support env var in value such as
        # %LOCALAPPDATA%\Plex Media Server\sageplex_cfg.json
        cfg = os.path.expandvars(cfg)

        # now try to open the file and read it
        try:
            with open(cfg) as data_file:
                self._data = json.load(data_file)
        except (IOError, ValueError), e:
            print "ERROR: %s: %s" % (cfg, e)

    # getters
    def getSagex(self):
        '''Return the sagex configuration data'''
        return self._data['sagex']

    def getScanLog(self):
        '''Return the scanner log location'''
        return os.path.expandvars(self._data['scan_log'])


def main():
    cfg = Config('SAGEPLEX_CFG')
    print cfg.getSagex()
    print cfg.getScanLog()
    
if __name__ == '__main__':
    import sys
    main()
