#####################################################################
#
# Author:  Raymond Chi
#
# simle wrapper class for logging that can work under both scanner
# (standalone python) and agent (PMS framework)
#
######################################################################

import logging, logging.handlers

# various log levels
CRITICAL = 50
ERROR    = 40
WARNING  = 30
INFO     = 20
DEBUG    = 10


class PlexLog(object):
    '''Wrapper for logging/Log for PMS

    Wrapper object for logging inside the scanner and agent. Uses
    logging module when under scanner, and uses PMS framework's Log
    method when under agent.
    '''

    def __init__(self, isAgent = False):
        '''Create a PlexLog object

        @param isAgent  are we running under PMS framework?
        '''
        self.isAgent = isAgent
        self.logPrefix = ''

    def setPrefix(self, prefix = None):
        '''Set a prefix for all the log messages

        The prefix will be used as is, no strings such as ": " will be
        appended after the prefix.

        @param prefix  a string prefix
        '''
        if prefix:
            self.logPrefix = prefix
        else:
            self.logPrefix = ''

    def log(self, lvl, msg, *args, **kwargs):
        '''write log with specific level

        @param lvl     log level
        @param args    optional arguments
        @param kwargs  optional keyward arguments
        '''
        msg = self.logPrefix + str(msg)

        if lvl == DEBUG:
            if self.isAgent:
                Log.Debug(msg, *args, **kwargs)
            else:
                logging.debug(msg, *args, **kwargs)
        elif lvl == WARNING:
            if self.isAgent:
                Log.Warn(msg, *args, **kwargs)
            else:
                logging.warning(msg, *args, **kwargs)
        elif lvl == ERROR:
            if self.isAgent:
                Log.Error(msg, *args, **kwargs)
            else:
                logging.error(msg, *args, **kwargs)
        elif lvl == CRITICAL:
            if self.isAgent:
                Log.Critical(msg, *args, **kwargs)
            else:
                logging.critical(msg, *args, **kwargs)
        else:
            if self.isAgent:
                Log.Info(msg, *args, **kwargs)
            else:
                logging.info(msg, *args, **kwargs)

    def updateLoggingConfig(self, filename, log_format, debug,
                            backups = 5, maxsize = 4*1024*1024):
        '''Update python logging configuration

        Update the python logging module's configuration to point to the
        specified file with the specified format

        @param filename    log path
        @param log_format  log format
        @param debug       enable debug log or not
        @param backups     number of backups to keep for rotating logs
        @param maxsize     max filesize before rotating logs
        '''
        if self.isAgent:
            # not for running under agent
            return
        # calculate level
        lvl = logging.DEBUG if debug else logging.INFO
        # create new rotating log handler
        fileh = logging.handlers.RotatingFileHandler(filename, 'a',
                                                     maxBytes=maxsize,
                                                     backupCount=backups)
        formatter = logging.Formatter(log_format)
        fileh.setFormatter(formatter)
        # update root logging's handler
        log = logging.getLogger()  # root logger
        log.setLevel(lvl)          # update level
        for hdlr in log.handlers:  # remove all old handlers
            log.removeHandler(hdlr)
        log.addHandler(fileh)      # set the new handler

    ## wrapper functions around log()

    def debug(self, msg, *args, **kwargs):
        return self.log(DEBUG, msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        return self.log(INFO, msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        return self.log(WARNING, msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        return self.log(ERROR, msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        return self.log(CRITICAL, msg, *args, **kwargs)


######################################################################

# for testing
def main():
    # basic format to console
    LOG_FORMAT = '%(asctime)s| %(levelname)-8s| %(message)s'
    logging.basicConfig(format=LOG_FORMAT, level=logging.DEBUG)

    mylog = PlexLog()
    #mylog.updateLoggingConfig('mytest.log', LOG_FORMAT, True, 5, 20)

    # all level without prefix
    mylog.debug('some debug message: %s', 'test123')
    mylog.info('some info message: %d', 314)
    mylog.warning('some warning message: %s', 'testabc')
    mylog.error('%s: some error message: %s', 'func', 'detail')
    mylog.critical('some critical message: %s', 'highest category')

    # all level with prefix
    mylog.setPrefix('***** ')
    mylog.debug('some debug message: %s', 'test123')
    mylog.info('some info message: %d', 314)
    mylog.warning('some warning message: %s', 'testabc')
    mylog.error('%s: some error message: %s', 'func', 'detail')
    mylog.critical('some critical message: %s', 'highest category')

    mylog.setPrefix()
    mylog.info('message with no prefix')

# uncomment to test as _ conflicts with PMS runtime
# if __name__ == '__main__':
#     import sys
#     main()

# python falsy values: None/False/0/''/{}
# function implicit return: None
