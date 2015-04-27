#####################################################################
#
# Author:  Raymond Chi
#
# Tool that synchronizes watched/resume status between Sage/Plex
#
######################################################################

# PLEX reg key for non-localhost access: disableRemoteSecurity="1"

import sys, logging, argparse, signal

import sageplex.plexlog  # log wrapper for scanner/agent
import sageplex.config   # read configuration files
import sageplex.sagex    # SageTV API calls
import sageplex.plexapi  # PLEX API calls
import sageplex.spvideo  # parsing sage/plex video obj

import pdb

PROG_DESC   = ('Compare or synchronize watch status and resume position '
               'of the specified PLEX library sections with SageTV. '
               'Individual PLEX Media files can be specified when the '
               '-m option is used.')
PROG_USAGE  = ('sageplex_sync.py [options] [id [id ...]]')

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
        self.updated = 0    # number of videos updated
        self.insync = 0     # number of videos in sync
        self.plex = []      # plex videos out of sync
        self.sage = []      # sage videos out of sync
        self.nosage = []    # videos not in sagetv

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
        '''add an out of sync plex title to list

        @param id        plex media-id of video
        @param title     name of video
        @param p_resume  plex resume position
        @param s_resume  sage resume position
        '''
        s = ('[%s] %s (%s vs %s)' %
             (id, title, p_resume, s_resume))
        self.plex.append(s)

    def addSage(self, id, title, s_resume, p_resume):
        '''add an out of sync sage title to list

        @param id        plex media-id of video
        @param title     name of video
        @param p_resume  plex resume position
        @param s_resume  sage resume position
        '''
        s = ('[%s] %s (%s vs %s)' %
             (id, title, s_resume, p_resume))
        self.sage.append(s)

    def addNoSage(self, id, title, p_resume):
        '''add an not in sage title to list

        @param id        plex media-id of video
        @param title     name of video
        @param p_resume  plex resume position
        '''
        s = ('[%s] %s (%s)' %
             (id, title, p_resume))
        self.nosage.append(s)

    def printSummary(self):
        '''Print accumulated statistics'''
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
    for x in args.id:
        if not x.isdigit():
            print 'Must be a PLEX Media-ID number: %s' % x
            continue
        path = '/library/metadata/%s' % x
        if args.sync:
            print 'Syncing media-id %s: %s' % (x, path)
        else:
            print 'Displaying media-id %s: %s' % (x, path)
        plexapi.walkPlex(path, None, processVideo)


def syncSections(args):
    '''Sync/info list of sections

    @param args  namespace from ArgumentParser.parse_args
    '''
    sections = None
    slist = []
    path = '/library/sections'

    # if all is specified, get all sections and add to work list
    if 'all' in args.id:
        sections = plexapi.listSections()
        slist.extend(sections.keys())
    else:
        # user entered a list of id/names
        # check if a name is specified
        namelist = [s for s in args.id if not s.isdigit()]
        if namelist:
            sections = plexapi.listSections(byName=True)
        # now loop through list and add to sections
        for x in args.id:
            if x.isdigit():
                slist.append(x)
            else:
                # a name, so we lookup its id
                section_id = sections.get(x)
                if section_id:
                    slist.append(section_id['id'])
                else:
                    print 'Section not found: %s' % x

    if not slist:
        return

    # now do the work
    if args.sync:
        print 'Sections to sync: %s' % slist
    else:
        print 'Sections to display: %s' % slist

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
    p_resume = pv.getResume()

    # if set explicit position, do it here before query sage
    if g_args.position:
        print '[set to %s]' % g_args.position
        print '\t  PLEX: %s' % pv.getInfo()
        if g_args.positionSec == p_resume:
            print '\t  No change needed, skipping.',
            return
        # now update PLEX media
        if not askUser(None, '\tUpdate media [%s]: %s?' %
                       (pv.id, pv.title), silent=(not g_args.prompt)):
            return
        print '\t  Updating PLEX ... ',
        sys.stdout.flush()
        if not g_args.simulate:
            # Plex seems to ignore starting pos under a minute
            plexapi.setProgress(pv.id, g_args.positionSec)
            g_stat.updated += 1
            print '[done]'
        else:
            print '[simulate]'
        return

    # get SagetV information for video file
    mf = sageapi.getMediaFileForName(pv.file)
    # mf = sample_mf()
    if not mf:
        print '[not in Sage]'
        log.info('file not in SageTV: %s', pv.file)
        g_stat.addNoSage(pv.id, pv.getTitle(), pv.getResumeStr())
        return
    sv = sageplex.spvideo.SageVideo(mf, log)
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
        if not g_args.sync:
            return
        # now update PLEX media
        if not askUser(None, '\tUpdate media [%s]: %s?' %
                       (pv.id, pv.title), silent=(not g_args.prompt)):
            return
        print '\t  Updating PLEX ... ',
        sys.stdout.flush()
        if not g_args.simulate:
            # Plex seems to ignore starting pos under a minute
            plexapi.setProgress(pv.id, s_resume)
            g_stat.updated += 1
            print '[done]'
        else:
            print '[simulate]'


def askUser(msg, prompt, default='n', silentDefault='y', silent=False):
    '''Ask the user a question

    @msg            message/text to display to the user
    @prompt         text for prompt
    @default        if user did not supply an answer
    @silentDefault  default if running in silent mode
    @silent         are we in silent mode
    '''
    if silent:
        default = silentDefault
    prompt += ' (y/n [%s]) ' % default

    if not silent:
        if msg:
            print msg
        answer = raw_input(prompt).strip()
        if not answer:
            answer = default
    else:
        answer = default

    if (answer.lower() != 'y'):
        return False
    else:
        return True


def mainSync(args):
    '''Sync/Display the PLEX library sections

    @param args  namespace from ArgumentParser.parse_args
    '''
    # this should not happen
    if not args.id:
        return

    # if user explicitly specified resume position
    if args.position:
        # prompt for confirmation
        msg = ('You have specified an explicit resume position: %s\n'
               'This will override resume position for all videos specified!\n' %
               args.position)
        if not askUser(msg, 'Are you sure you want to continue?'):
            return

    # are we syncing individual media
    if args.media:
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
    parser = argparse.ArgumentParser(epilog = PROG_DESC,
                                     usage = PROG_USAGE,
                                     formatter_class = argparse.ArgumentDefaultsHelpFormatter)

    # list or sync can't be both used
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-l', '--list',
                        help='list PLEX library sections',
                        action='store_true')
    group.add_argument('-s', '--sync',
                        help='sync watch status',
                        action='store_true')

    # rest of parameters
    parser.add_argument('-m', '--media',
                        help='ID is media-id, not section-id',
                        action='store_true')
    parser.add_argument('--position',
                        help='Set explicit resume position (h:m:s)',
                        default=None)
    parser.add_argument('-x', dest='ignore', type=int,
                        help='ignore if pos within initial x seconds',
                        default=60)
    parser.add_argument('-p', dest='prompt',
                        help='confirm each update',
                        action='store_true')
    parser.add_argument('-n', dest='simulate',
                        help='do nothing, simulate operation',
                        action='store_true')

    # 0 or more IDs to operate on, this could be library section id
    # or media id.
    parser.add_argument('id', nargs='*',
                        help='PLEX library ID/name/all',
                        default=None)

    # parse the arguments
    args = parser.parse_args()
    # print args

    # do some sanity check on parameters
    if args.position:
        # must be in media-id mode, not section mode
        if not args.media:
            print 'Error: must use individual Media-ID (-m) for explicit resume position!'
            return
        # must be in sync mode
        if not args.sync:
            print 'Sync mode (-s) is required for explicit resume position!'
            return
        # should be in h:m:s format
        t = args.position.split(':')
        if len(t) > 3:
            print 'Invalid resume position: format error: %s' % args.position
            return
        # check and convert time to seconds
        s = 0
        i = 0
        for x in reversed(t):
            if not x.isdigit():
                print 'Invalid resume position: non digit: %s' % args.position
                return
            s += int(x) * (60**i)
            i += 1
        args.positionSec = s * 1000  # in ms

    # any work to do?
    if args.list or args.id:
        return args
    else:
        parser.print_help()


def main():
    '''Main entrypoint'''
    global mycfg, mylog, sageapi, plexapi
    global g_args, g_stat

    # parse arguments
    args = parseArgs()
    if not args:
        return
    g_args = args

    # parameter is OK, initialize logs/config object
    logging.basicConfig(format=LOG_FORMAT, level=logging.DEBUG,
                        filename='sageplex_sync.log')
    mylog = sageplex.plexlog.PlexLog()  # log wrapper
    mylog.info('***** Entering SagePlex Sync *****')

    # create cfg/sage/plex global objects
    mycfg = sageplex.config.Config(sys.platform)

    # check cfg file is read correctly
    if not mycfg.getPlexHost():
        print 'PLEX host is not defined!\nCheck sageplex_cfg.json to ensure it is valid.\nCheck sageplex_sync.log for additional details.'
        return
    if not mycfg.getSagexHost():
        print 'SageX host is not defined!\nCheck sageplex_cfg.json to ensure it is valid.\nCheck sageplex_sync.log for additional details.'
        return

    sageapi = sageplex.sagex.SageX(mycfg.getSagexHost())
    plexapi = sageplex.plexapi.PlexApi(mycfg.getPlexHost())

    # register our ctrol-c handler to gracefully exit.
    mylog.info('registering SIGINT handler ...')
    signal.signal(signal.SIGINT, signal_handler)

    # now do the work
    g_stat = Stat()
    if args.list:
        mainList(args)
    else:
        mainSync(args)
        mylog.info('')  # done, write empty line so we have good separator for next time


if __name__ == '__main__':
    main()

# useful stuff
# python falsy values: None/False/0/''/{}
# function implicit return: None
