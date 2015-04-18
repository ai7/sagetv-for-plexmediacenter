#####################################################################
#
# Author:  Raymond Chi
#
# Tool that synchronizes watched/resume status between Sage/Plex
#
######################################################################

import sys, logging, argparse, signal

import sageplex.plexlog  # log wrapper for scanner/agent
import sageplex.config   # read configuration files
import sageplex.sagex    # SageTV API calls
import sageplex.plexapi  # PLEX API calls
import sageplex.spvideo  # parsing sage/plex video obj

import pdb


__version__ = '1.0.0.' + '$Revision: #1 $'[12:-2]
__date__    = '$Date: 2015/04/17 $'[7:-2].replace('/','-')

PROG_NAME   = 'SagePlex Sync'
PROG_VER    = 'v%s (%s)' % (__version__, __date__)

PROG_NAME_MAIN = PROG_NAME + ' ' + PROG_VER

LOG_FORMAT = '%(asctime)s| %(levelname)-8s| %(message)s'

mycfg = None
mylog = None
sageapi = None
plexapi = None

g_args = None
g_exit = False  # signal script to gracefully exit
g_stat = None


######################################################################
# catch control-c
######################################################################

def signal_handler(signal, frame):
    logging.error('SIGINT detected!')
    global g_exit
    g_exit = True


######################################################################
# statistics object
######################################################################

class Stat:
    '''keeps track of statistics'''
    def __init__(self):
        self.processed = 0  # number of videos processed
        self.updated = 0    # number of plex videos updated
        self.insync = 0     # number of videos in sync
        self.plex = []      # plex video out of sync
        self.sage = []      # sage video out of sync
        self.nosage = []    # not in sagetv

    # convert to string
    def __str__(self):
        s = '%d videos' % self.processed
        if self.insync:
            s += ', %d in-sync' % self.insync
        if self.plex:
            s += ', %d PLEX out-of-sync' % len(self.plex)
        if self.sage:
            s += ', %d SageTV out-of-sync' % len(self.sage)
        if self.nosage:
            s += ', %d not in SageTV' % len(self.nosage)
        if self.updated:
            s += ', %d updated' % self.updated
        return s

    def addPlex(self, id, title, p_resume, s_resume):
        '''add an out of sync plex title to list'''
        s = ('[%s] %s (%s vs %s)' %
             (id, title, p_resume, s_resume))
        self.plex.append(s)

    def addSage(self, id, title, s_resume, p_resume):
        '''add an out of sync sage title to list'''
        s = ('[%s] %s (%s vs %s)' %
             (id, title, s_resume, p_resume))
        self.sage.append(s)

    def addNoSage(self, id, title, p_resume):
        '''add an not in sage title to list'''
        s = ('[%s] %s (%s)' %
             (id, title, p_resume))
        self.nosage.append(s)

    def printSummary(self):
        '''Output statistics'''
        # print summary and statistics
        if g_stat.plex:
            print '\nPLEX out of sync:'
            for s in g_stat.plex:
                print '\t' + s
        if g_stat.sage:
            print '\nSageTV out of sync:'
            for s in g_stat.sage:
                print '\t' + s
        if g_stat.nosage:
            print '\nNot in SageTV:'
            for s in g_stat.nosage:
                print '\t' + s
        print '\nTotal: %s.' % g_stat


######################################################################
# list PLEX library sections
######################################################################

def mainList(args):
    '''List PLEX library sections

    @param args  namespace from ArgumentParser.parse_args
    '''
    sections = plexapi.listSections()
    if not sections:
        print 'Failed to retrieve sections!'
        return
    for s in sections:
        if g_exit:
            mylog.error('Got SIGINT, exiting!!')
            break
        # output similar to what plex scanner outputs
        print '%3s: %s (%s)' % (s,
                                sections[s].get('title'),
                                sections[s].get('type'))


######################################################################
# run info/sync
######################################################################


def syncMediaId(args):
    '''Sync/info particular media-id

    @param args  namespace from ArgumentParser.parse_args
    '''
    path = '/library/metadata/%s' % args.id
    if args.mode == 'i':
        print 'Displaying media-id %s: %s' % (args.id, path)
    else:
        print 'Syncing media-id %s: %s' % (args.id, path)
    plexapi.walkPlex(path, None, processVideo)


def syncSections(args):
    '''Sync/info list of sections

    @param args  namespace from ArgumentParser.parse_args
    '''
    # if section is specified, use it, otherwise sync all sections
    slist = []
    path = '/library/sections'
    if args.section:
        slist.append(args.section)
    else:
        sections = plexapi.listSections()
        slist.extend(sections.keys())

    if args.mode == 'i':
        print 'Sections to display: %s' % slist
    else:
        print 'Sections to sync: %s' % slist

    for s in slist:
        path = ('/library/sections/%s/all' % s)
        print 'Syncing section %s: %s' % (s, path)
        plexapi.walkPlex(path, None, processVideo)


def processVideo(node, log):
    '''Process the video node and synchronize the resume position

    For now this is one way, from Sage -> Plex

    @param node   xml <Video> node
    @param log    the log object
    '''
    # check if we need to exit (ctrl-c)
    if g_exit:
        mylog.error('Got SIGINT, exiting!!')
        sys.exit(1)
    g_stat.processed += 1

    # first get the PlexVideo info from XML data
    pv = sageplex.spvideo.PlexVideo(node, log)
    print '  %s' % str(pv).encode('ascii', 'ignore'),
    sys.stdout.flush()

    # get SagetV information for video file
    mf = sageapi.getMediaFileForName(pv.file)
    # mf = sample_mf()
    if not mf:
        print '[no Sage]'
        log.info('file not in SageTV: %s', pv.file)
        g_stat.addNoSage(pv.id, pv.getTitle(), pv.getResumeStr())
        return
    sv = sageplex.spvideo.SageVideo(mf, log)

    # now compare the resume time and decide what to do
    p_resume = pv.getResume()
    s_resume = sv.getResume()

    # if in sync (or both 0), no changes needed
    if p_resume == s_resume:
        g_stat.insync += 1
        print '[OK]'
        return

    # if only one is zero, and other is within 1 min of start
    if (not p_resume) or (not s_resume):
        ignore = int(g_args.ignore) * 1000
        if ((p_resume and p_resume < ignore) or
            (s_resume and s_resume < ignore)):
            # in sync, no changes needed
            g_stat.insync += 1
            print '[OK < %ss]' % g_args.ignore
            return

    # sage is out of sync
    if s_resume < p_resume:
        g_stat.addSage(pv.id, pv.title, sv.getResumeStr(None),
                       pv.getResumeStr(None))
        print '[Sage out of sync]'
        print '\t  Sage: %s' % sv
        print '\t  PLEX: %s' % pv.getInfo()
        # do nothing for now
        return

    # plex is out of sync
    if p_resume < s_resume:
        g_stat.addPlex(pv.id, pv.title, pv.getResumeStr(None),
                       sv.getResumeStr(None))
        print '[PLEX out of sync]'
        print '\t  PLEX: %s' % pv.getInfo()
        print '\t  Sage: %s' % sv
        # if info mode, done
        if g_args.mode == 'i':
            return
        # else update
        # TODO: prompt user if requested
        print '\t  Updating PLEX ... ',
        sys.stdout.flush()
        if not g_args.simulate:
            # TODO: plex seems to not set anything under a minute?
            plexapi.setProgress(pv.id, s_resume)
            g_stat.updated += 1
            print '[done]'
        else:
            print '[simulate]'


def mainSync(args):
    '''Sync/Display the PLEX library sections

    @param args  namespace from ArgumentParser.parse_args
    '''
    # check if a id is specified
    if args.id:
        syncMediaId(args)
    else:
        syncSections(args)

    # done print summary
    g_stat.printSummary()


######################################################################
# main functions
######################################################################

def parseArgs():
    '''Parse command line arguments

    @return  namespace from ArgumentParser.parse_args
    '''
    # add the parent parser
    parser = argparse.ArgumentParser(description = PROG_NAME_MAIN)

    # create a set of subcommand parsers
    subparsers = parser.add_subparsers(help='command (-h for more help)',
                                       dest='mode')

    # list PLEX libraries
    parser_c = subparsers.add_parser('l', help='list PLEX library sections')

    # display PLEX/SageTV libraries
    parser_e = subparsers.add_parser('i', help='show library watch status')
    parser_e.add_argument('-c', dest='section',
                          help='A PLEX library section ID',
                          default=None)
    parser_e.add_argument('-m', dest='id',
                          help='A PLEX media ID',
                          default=None)
    parser_e.add_argument('-x', dest='ignore', type=int,
                          help='ignore if resume pos within initial x seconds [60]',
                          default=60)

    # sync PLEX/SageTV libraries
    parser_e = subparsers.add_parser('s', help='sync library watch status')
    parser_e.add_argument('-c', dest='section',
                          help='A PLEX library section ID',
                          default=None)
    parser_e.add_argument('-m', dest='id',
                          help='A PLEX media ID',
                          default=None)
    parser_e.add_argument('-x', dest='ignore', type=int,
                          help='ignore if resume pos within initial x seconds [60]',
                          default=60)
    parser_e.add_argument('-p', dest='prompt',
                          help='confirm each update',
                          action='store_true')
    parser_e.add_argument('-n', dest='simulate',
                          help='do nothing, simulate operation',
                          action='store_true')

    # return the parsed namespace
    return parser.parse_args()


def main():
    '''Main entrypoint'''
    global mycfg, mylog, sageapi, plexapi
    global g_args, g_stat
    # parse arguments
    args = parseArgs()
    g_args = args
    # do the actions
    if args.mode in ['l', 'i', 's']:
        # parameter is OK, initialize logs/config object to do work
        logging.basicConfig(format=LOG_FORMAT, level=logging.DEBUG,
                            filename='sageplex_sync.log')
        mylog = sageplex.plexlog.PlexLog()  # log wrapper
        mylog.info('***** Entering SagePlex Sync *****')

        # create cfg/sage/plex global objects
        mycfg = sageplex.config.Config(sys.platform)
        sageapi = sageplex.sagex.SageX(mycfg.getSagexHost())
        plexapi = sageplex.plexapi.PlexApi(mycfg.getPlexHost())

        # register our ctrol-c handler to gracefully exit.
        mylog.info('registering SIGINT handler ...')
        signal.signal(signal.SIGINT, signal_handler)

        # now do the work
        g_stat = Stat()
        if args.mode == 'l':
            mainList(args)
        elif args.mode == 's' or args.mode == 'i':
            mainSync(args)
        mylog.info('')  # done, write empty line so we have good separator for next time
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

# useful stuff
# python falsy values: None/False/0/''/{}
# function implicit return: None
