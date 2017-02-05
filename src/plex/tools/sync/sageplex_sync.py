#####################################################################
#
# Author:  Raymond Chi
#
# Tool that synchronizes watched/resume status between Sage/Plex
#
# SageTV and PLEX handles watch status and resume position
# differently. This adds some complication to the sync logic.
#
# After watching a show, PLEX will rewind the position to the
# beginning, while SageTV's position will remain at the end. We need
# to recognize these as the same.
#
# PLEX stores a watched count, and will increment it when you rewatch
# a show. So the status remains watched in a sense, while the resume
# position starts from the beginning and continue on.
#
# SageTV on the other hand will clear the watched status when you
# rewatch a show. So in essense, it only has three states, unwatched,
# unwatched with some resume position, and watched. Furthermore,
# setting resume position on a watched show is apparently a no-op. So
# need to clear watch status before we can set a resume position.
#
######################################################################

# PLEX reg key for non-localhost access: disableRemoteSecurity="1"

import os, sys, logging, argparse, signal, pprint

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

def watchedToStr(watched):
    '''Return watched status as string

    @param watched  boolean
    '''
    return 'watched' if watched else 'not watched'


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

    def addPlex(self, id, title, p_resume, s_resume, p_watch, s_watch):
        '''add an out of sync plex title to list

        @param id        plex media-id of video
        @param title     name of video
        @param p_resume  plex resume position
        @param s_resume  sage resume position
        @param p_watch   plex watched status
        @param s_watch   sage watched status
        '''
        s = ('[%s] %s (%s [%s] vs %s [%s])' %
             (id, title,
              p_resume, watchedToStr(p_watch),
              s_resume, watchedToStr(s_watch)))
        self.plex.append(s)

    def addSage(self, id, title, s_resume, p_resume, s_watch, p_watch):
        '''add an out of sync sage title to list

        @param id        plex media-id of video
        @param title     name of video
        @param s_resume  sage resume position
        @param p_resume  plex resume position
        @param s_watch   sage watched status
        @param p_watch   plex watched status
        '''
        s = ('[%s] %s (%s [%s] vs %s [%s])' %
             (id, title,
              s_resume, watchedToStr(s_watch),
              p_resume, watchedToStr(p_watch)))
        self.sage.append(s)

    def addNoSage(self, id, title, p_resume, p_watch):
        '''add an not in sage title to list

        @param id        plex media-id of video
        @param title     name of video
        @param p_resume  plex resume position
        @param p_watch   plex watched status
        '''
        s = ('[%s] %s (%s [%s])' %
             (id, title, p_resume, watchedToStr(p_watch)))
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
        if not sections:
            print 'Failed to retrieve sections!'
            return
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
    '''Process the video node and synchronize the resume position and
    watched status.

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
    pn_resume = pv.getResumeNorm()

    # if set explicit position, do it here before query sage
    # XXX: clean up this block
    if g_args.position:
        print '[set to %s]' % g_args.position
        print '\t  PLEX: %s' % pv.getInfo()
        if g_args.positionSec == pv.getResume():
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
        g_stat.addNoSage(pv.id, pv.getTitle(), pv.getResumeStr(), pv.getWatched())
        return
    sv = sageplex.spvideo.SageVideo(mf, log)
    sn_resume = sv.getResumeNorm()
    airing = mf.get('Airing')

    # if asking to dump sage data, dump and exit
    if g_args.sagedata:
        print '\n'
        pprint.pprint(mf)
        return

    # ***** now perform the sync *****

    watched_sync = False  # are watch status in sync
    pos_sync = False      # are resume position in sync
    reason = ''           # extra text for console output
    ignore = int(g_args.ignore) * 1000

    # 1. check whether the watched status is in sync or not
    watched_sync = sv.getWatched() == pv.getWatched()

    # 2. check whether resume position is in sync or not.
    if (pn_resume == sn_resume or abs(pn_resume - sn_resume) < 2000):
        # The 2 second difference is needed because setting the resume
        # position in Sage does not yield exact ms result as PLEX pos.
        reason = '[OK]'
        pos_sync = True

    # plex: watched, pos at 20m
    # sage: not watched, pos at 20m
    # need to consider this as watch status in sync
    # if sage is not watched, pos is in sync and > 0
    if pos_sync and sn_resume > 0:
        if not sv.getWatched() and pv.getWatched():
            watched_sync = True
            reason = '[Ok]'

    # 3. if both watched/position are in sync, we are done
    if watched_sync and pos_sync:
        g_stat.insync += 1
        print reason
        if g_args.media:
            # print detailed timing info
            print '\t  Sage: %s' % sv.getInfo(g_args.media) # detail if individual media
            print '\t  PLEX: %s' % pv.getInfo()
        return

    # 4. watched/pos are not in sync, now do the syncing

    # - if resume position needs sync, more recent one takes effect
    #     sage: clear watch status if watched, then set pos
    #     plex: set pos
    #     done, do not sync watch status (as doing so clears pos)
    # - if watch status needs sync
    #     sync only one way, from unwatched -> watched
    if not pos_sync:
        if sv.lastWatched < pv.lastWatched:
            # sync sage pos with PLEX data
            updateSage(sv, pv, airing, syncPos=True)
        else:
            # sync plex pos with Sage data
            updatePlex(pv, sv, syncPos=True)
    elif not watched_sync:
        if sv.getWatched():  # Sage true PLEX must be false
            assert(not pv.getWatched())
            updatePlex(pv, sv, syncStatus=True)
        elif pv.getWatched():  # PLEX true sage must be false
            assert(not sv.getWatched())
            updateSage(sv, pv, airing, syncStatus=True)
        else:
            assert(False)
    else:
        assert(False)


def updatePlex(pv, sv, syncStatus=False, syncPos=False):
    '''Update PLEX metadata from Sage

    @param pv          PlexVideo object
    @param sv          SageVideo object
    @param syncStatus  are we updating watch status?
    @param syncPos     are we updating pos?
    '''
    if not syncStatus and not syncPos:
        return

    g_stat.addPlex(pv.id, pv.title,
                   pv.getResumeStr(None), sv.getResumeStr(None),
                   pv.getWatched(), sv.getWatched())
    print '[PLEX out of sync]'
    print '\t  PLEX: %s' % pv.getInfo()
    print '\t  Sage: %s' % sv.getInfo(g_args.media) # detail if individual media
    # if info mode, done
    if not g_args.sync:
        return
    # now update PLEX media
    if not askUser(None, '\tUpdate PLEX media [%s]: %s?' %
                   (pv.id, pv.title), silent=(not g_args.prompt)):
        return
    print '\t  Updating PLEX ...',
    sys.stdout.flush()
    # now set watched status on PLEX
    if syncStatus:
        print '[watched]',
        if not g_args.simulate:
            plexapi.setWatched(pv.id, True)
    elif syncPos:
        # Plex seems to ignore starting pos under a minute
        print '[pos]',
        if not g_args.simulate:
            plexapi.setProgress(pv.id, sv.resume)
    else:
        assert(False)

    # output done message
    if not g_args.simulate:
        g_stat.updated += 1
        print '[done]'
    else:
        print '[simulate]'


def updateSage(sv, pv, airing, syncStatus=False, syncPos=False):
    '''Update Sage metadata from PLEX

    @param sv          SageVideo object
    @param pv          PlexVideo object
    @param airing      mf airing object
    @param syncStatus  are we updating watch status?
    @param syncPos     are we updating pos?
    '''
    if not syncStatus and not syncPos:
        return

    g_stat.addSage(pv.id, pv.title,
                   sv.getResumeStr(None), pv.getResumeStr(None),
                   sv.getWatched(), pv.getWatched())
    print '[Sage out of sync]'
    print '\t  Sage: %s' % sv.getInfo(g_args.media) # detail if individual media
    print '\t  PLEX: %s' % pv.getInfo()
    # if info mode, done
    if not g_args.sync:
        return
    # now update Sage media
    if not askUser(None, '\tUpdate Sage media [%s]: %s?' %
                   (pv.id, pv.title), silent=(not g_args.prompt)):
        return
    print '\t  Updating Sage ...',
    sys.stdout.flush()
    # now set watched status on Sage
    if syncStatus:
        print '[watched]',
        if not g_args.simulate:
            sageapi.setWatched(airing.get('AiringID'))
    elif syncPos:
        # sage don't take a duration?
        print '[pos]',
        if not g_args.simulate:
            if sv.getWatched():
                # if sage is watched, clear it, as we can't set pos if
                # it's in watched state.
                print '[- watched]',
                sageapi.clearWatched(airing.get('AiringID'))
            if pv.resume:
                # if have plex resume pos, set it
                sageapi.setWatchedTimes(airing.get('AiringID'),
                                        airing.get('AiringStartTime') + pv.resume,
                                        pv.lastWatched * 1000 - pv.resume)
            else:
                # no plex resume pos, plex must be watched, set sage
                # watched flag. this is because we are copying a plex
                # pos 0 to sage, which must mean this is a plex
                # watched show. damn this is complicated! :)
                assert(pv.getWatched())
                print '[watched]',
                sageapi.setWatched(airing.get('AiringID'))
    else:
        assert(False)

    # output done message
    if not g_args.simulate:
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
# add sage tv/movie sections
######################################################################

def mainAdd(args):
    '''Add a PLEX library section'''
    if args.addtv:
        ans = plexapi.createSection(args.addtv[0], args.addtv[1:])
    elif args.addmovie:
        ans = plexapi.createSection(args.addmovie[0], args.addmovie[1:],
                                    stype='movie',
                                    agent='com.plexapp.agents.imdb',
                                    scanner='SageTV Movie Scanner')
    else:
        print 'mainAdd: unsupported case'
        return

    if not ans:
        print 'Failed to add PLEX section. Check log for details.'
        return

    mylog.info('PLEX library created.')


######################################################################
# delete PLEX library sections
######################################################################

def mainDelete(args):
    '''Delete a PLEX library section'''
    # get the section name
    sections = plexapi.listSections()
    if not sections:
        print 'No libraries found on PLEX server.'
        return
    s = sections.get(args.delsec)
    if not s:
        print 'Library [%s] not found!' % args.delsec
        return
    # ask user to confirm
    if not askUser('Are you sure you want to delete the library %s?\n\n'
                   'This cannot be undone!\n' % s.get('title'),
                   'Delete Library [%s]?' % args.delsec):
        return
    # now delete it
    ans = plexapi.deleteSection(args.delsec)
    if ans is None:
        print 'Library not found: %s' % args.delsec
    else:
        print 'Library %s deleted.' % args.delsec


######################################################################
# refresh PLEX library sections
######################################################################

def mainRefresh(args):
    '''Refresh a PLEX library section'''
    # get the section name
    sections = plexapi.listSections()
    if not sections:
        print 'No libraries found on PLEX server.'
        return
    s = sections.get(args.refresh)
    if not s:
        print 'Library [%s] not found!' % args.refresh
        return
    # now do the refresh
    print 'Refreshing library [%s]: %s' % (args.refresh, s.get('title'))
    plexapi.refreshSection(args.refresh)


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
    parser.add_argument('--sagedata',
                        help='dump SageTV data for media-id',
                        action='store_true')
    parser.add_argument('--position',
                        help='Set explicit resume position (h:m:s)',
                        default=None)
    parser.add_argument('-x', dest='ignore', type=int,
                        help='ignore if pos within initial x seconds',
                        default=60)
    parser.add_argument('-p', dest='prompt',
                        help='confirm each sync update',
                        action='store_true')
    parser.add_argument('-n', dest='simulate',
                        help='do nothing, simulate sync operation',
                        action='store_true')
    # stuff for adding a library
    group.add_argument('--addtv', metavar=('NAME', 'PATH'), nargs='+',
                       help='add PLEX library for Sage TV shows',
                       default=False)
    group.add_argument('--addmovie', metavar=('NAME', 'PATH'), nargs='+',
                       help='add PLEX library for Sage Movies',
                       default=False)
    # deleting a library
    group.add_argument('--delsec', metavar='ID',
                       help='delete a PLEX library section',
                       default=None)
    # refresh a library
    group.add_argument('--refresh', metavar='ID',
                       help='refresh a PLEX library section',
                       default=None)

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

    # python argparse don't support 2+ as nargs, so check here
    if args.addtv and len(args.addtv) < 2:
        print 'Error: must specify at least one path with --addtv option!'
        return
    if args.addmovie and len(args.addmovie) < 2:
        print 'Error: must specify at least one path with --addmovie option!'
        return

    if args.sagedata:
        # must be in media-id mode, not section mode
        if not args.media:
            print 'Error: must use individual Media-ID (-m) for Sage data dump!'
            return

    # any work to do?
    if (args.list or args.id or
        args.addtv or args.addmovie or
        args.delsec or args.refresh):
        return args
    else:
        parser.print_help()


def setupLogging():
    '''Setup logging for sageplex_sync

    log files are put in %temp%, and will rotate once reaching 5MB
    with up to 5 backup files.
    '''
    global mylog

    # put logs in temp
    tmploc = os.path.expandvars('$TEMP')
    if tmploc == '$TEMP':
        tmploc = ''
    logloc = os.path.join(tmploc, 'sageplex_sync.log')

    # log wrapper
    mylog = sageplex.plexlog.PlexLog()
    mylog.updateLoggingConfig(logloc, LOG_FORMAT, True) # rotate handler
    mylog.info('***** Entering SagePlex Sync %s *****', sys.argv[1:])


def main():
    '''Main entrypoint'''
    global mycfg, sageapi, plexapi
    global g_args, g_stat

    # parse arguments
    args = parseArgs()
    if not args:
        return
    g_args = args

    # parameter is OK, initialize logs/config object
    setupLogging()

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
    plexapi = sageplex.plexapi.PlexApi(mycfg.getPlexHost(), token=mycfg.getPlexToken())

    # register our ctrol-c handler to gracefully exit.
    mylog.info('registering SIGINT handler ...')
    signal.signal(signal.SIGINT, signal_handler)

    # now do the work
    g_stat = Stat()
    if args.list:
        mainList(args)
    elif args.addtv or args.addmovie:
        mainAdd(args)
    elif args.delsec:
        mainDelete(args)
    elif args.refresh:
        mainRefresh(args)
    else:
        mainSync(args)
        mylog.info('')  # done, write empty line so we have good separator for next time


if __name__ == '__main__':
    main()

# useful stuff
# python falsy values: None/False/0/''/{}
# function implicit return: None
