#!/usr/bin/env python

#
# Installer for SageTV For PLEX Media Server for Windows/Mac/Linux.
#
# install:   python sageplex_install.py -i
# uninstall: python sageplex_install.py -u
#

import os, sys, argparse, logging, shutil, json

PROG_DESC   = ('Install/Uninstall/Configure SageTV for PLEX Media Server.')
LOG_FORMAT = '%(asctime)s| %(levelname)-8s| %(message)s'

# default PMS data location
LOC_WIN = [ r'%LOCALAPPDATA%\Plex Media Server',
            r'%USERPROFILE%\Local Settings\Application Data\Plex Media Server' ]
LOC_MAC = [ '~/Library/Application Support/Plex Media Server' ]
LOC_LIN = [ '~plex/Library/Application Support/Plex Media Server' ]

CFG_FILE = 'sageplex_cfg.json'

g_root = ''  # script location
g_step = 1   # UI step count

isWin = False
isMac = False
isLin = False


######################################################################
# instutil
######################################################################

def getRegValue(root, key, value):
    '''Read a registry setting

    @param root   root, such as HKEY_LOCAL_MACHINE
    @param path   registry path
    @param key    key to retrieve value for
    @return       registry value or None
    '''
    logging.info('Querying REGKEY: %s\\%s', key, value)
    try:
        aReg = wreg.ConnectRegistry(None, wreg.HKEY_LOCAL_MACHINE)
        aKey = wreg.OpenKey(aReg, r'SOFTWARE\Frey Technologies')
        val, vtype = wreg.QueryValueEx(aKey, "LastInstallDir")
        logging.info('  value: %s', val)
    except OSError as e:
        logging.info('  not found: %s', e)
        val = None
    return val


def copyFile(src, dst, isTree=False, nukeDst=False):
    '''Copies individual files or directory tree

    @param src      source file/folder
    @param dst      destination file/folder
    @param isTree   is source a folder
    @param nukeDst  nuke destination before copy
    @return         True on success
    '''
    # if current directory is not the same as where the script is
    # located, then we need to prefix the source with the path to the
    # script. Otherwise we don't prefix so the path are shorter and
    # logs more readable.
    if g_root != os.getcwd():
        src = os.path.join(g_root, src)

    logging.info('Copying %s -> %s', src, dst)
    try:
        if isTree:
            if nukeDst and os.path.isdir(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
    except IOError as e:
        logging.error(str(e))
        return None

    return True


def deleteFile(f, isTree=False):
    '''Delete file or directory tree

    @param f       file/folder to delete
    @param isTree  is input a folder tree
    @return        True on success.
    '''
    logging.info('Deleting %s', f)

    if not os.path.exists(f):
        logging.warning('Not exist: %s', f)
        return True

    try:
        if isTree:
            shutil.rmtree(f)
        else:
            os.remove(f)
    except IOError as e:
        logging.error(str(e))
        return None

    return True


######################################################################
# question functions
######################################################################

def askUser(msg, prompt, default='n', silentDefault='y', silent=False):
    '''Ask the user a question

    @msg            message/text to display to the user
    @prompt         text for prompt
    @default        if user did not supply an answer
    @silentDefault  default if running in silent mode
    @silent         are we in silent mode
    @return         whether user answered y or not
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


def askSettings(msg, default):
    '''Get a setting from the user

    @param msg      message
    @param default  default value if user press enter
    @return         user reply or None
    '''
    prompt = '%s [%s]: ' % (msg, default)
    answer = raw_input(prompt).strip()
    return answer


######################################################################
# detection functions
######################################################################

def detectSageWin():
    '''Detect SageTV install location

    @return  SageTV.exe location, or None
    '''
    print 'Detecting SageTV ...',
    sys.stdout.flush()

    # look up sagetv location in
    # HKEY_LOCAL_MACHINE\SOFTWARE\Frey Technologies\LastInstallDir
    val = getRegValue(wreg.HKEY_LOCAL_MACHINE,
                      r'SOFTWARE\Frey Technologies',
                      'LastInstallDir')
    if not val:
        print '[Not Found]'
        return
    print '[%s]' % val

    # do some sanity test
    if not os.path.isdir(val):
        logging.error('SageTV dir does not exist: %s', val);
        print 'SageTV dir does not exist:', val
        return

    sagePath = os.path.join(val, 'SageTV')
    sageExe = os.path.join(val, r'SageTV\SageTV.exe')
    if not os.path.isfile(sageExe):
        logging.error('SageTV.exe not found: %s', sageExe);
        print 'SageTV.exe not found:', sageExe
        return
    logging.info('Found: %s', sageExe);

    return sagePath


def detectSage():
    '''Detect SageTV install location'''
    if isWin:
        return detectSageWin()
    # no mac/lin version


def detectPlexLoc(pList):
    '''Detect PLEX Data location on Windows

    @param pList  list of locations to check, expanded
    @return       PLEX data location
    '''
    logging.info('Detecting PLEX Data folder ...')
    ploc = None
    for p in pList:
        if os.path.isdir(p):
            logging.info('  Found: %s', p)
            ploc = p
            break
        logging.info('  Not exist: %s', p)
    if not ploc:
        return

    # now sanity check the directory
    if not os.path.isdir(os.path.join(ploc, 'Plug-ins')):
        logging.error('Data folder missing Plug-ins: %s', ploc)
        return

    return ploc


def expandVarsUser(x):
    '''expand both $ and ~ in string'''
    if '~' in x:
        return os.path.expanduser(x)
    else:
        return os.path.expandvars(x)


def detectPlex():
    '''Detect PLEX install location'''

    print 'Detecting PLEX ...',
    sys.stdout.flush()
    ploc = None

    if isWin:
        ploc = detectPlexLoc(expandVarsUser(x) for x in LOC_WIN)
    elif isMac:
        ploc = detectPlexLoc(expandVarsUser(x) for x in LOC_MAC)
    elif isLin:
        ploc = detectPlexLoc(expandVarsUser(x) for x in LOC_LIN)
    else:
        assert(0)

    if ploc:
        print '[%s]' % ploc
    else:
        print '[Not Found]'

    return ploc


######################################################################
# install functions
######################################################################

def copySageFiles(sagePath):
    '''Copy sagetv files

    @param sagePath  path to sagetv.exe
    @return          True on success
    '''
    global g_step

    # copy sagetv\sagex\services\plex.js to
    # [sagepath]\sagex\services\
    src = r'sagetv\sagex\services\plex.js'
    dst = os.path.join(sagePath, r'sagex\services\plex.js')

    print '[%d] Copying sagex extension ...' % g_step,
    sys.stdout.flush()
    g_step += 1

    if not copyFile(src, dst):
        print '[Failed]'
        return
    print '[OK]'

    return True


def removeSageFiles(sagePath):
    '''Remove sagetv files

    @param sagePath  path to sagetv.exe
    @return          True on success
    '''
    global g_step

    # [sagepath]\sagex\services\plex.js
    dst = os.path.join(sagePath, r'sagex\services\plex.js')

    print '[%d] Deleting sagex extension ...' % g_step,
    sys.stdout.flush()
    g_step += 1

    if not deleteFile(dst):
        print '[Failed]'
        return
    print '[OK]'

    return True


def copyPlexFiles(plexPath):
    '''Copy PLEX files

    @param plexPath  path to PLEX data folder
    @return          True on success
    '''
    global g_step

    # copy scanners
    src = r'plex/Scanners/Movies'
    dst = os.path.join(plexPath, r'Scanners/Movies')

    print '[%d] Copying PLEX Scanners ...' % g_step,
    sys.stdout.flush()
    g_step += 1

    if not copyFile(src, dst, isTree=True, nukeDst=True):
        print '[Failed]'
        return
    print '[OK]',

    src = r'plex/Scanners/Series'
    dst = os.path.join(plexPath, r'Scanners/Series')

    if not copyFile(src, dst, isTree=True, nukeDst=True):
        print '[Failed]'
        return
    print '[OK]'

    # copy bmt agent
    print '[%d] Copying PLEX Agent ...' % g_step,
    sys.stdout.flush()
    g_step += 1

    src = r'plex/Plug-ins/BMTAgentTVShows.bundle'
    dst = os.path.join(plexPath, r'Plug-ins/BMTAgentTVShows.bundle')

    if not copyFile(src, dst, isTree=True, nukeDst=True):
        print '[Failed]'
        return
    print '[OK]'

    print '[%d] Copying sageplex_cfg.json ...' % g_step,
    sys.stdout.flush()
    g_step += 1

    # setup sageplex_cfg.json file
    src = r'plex/sageplex_cfg.json'
    dst = os.path.join(plexPath, CFG_FILE)

    cfgExist = False
    if not os.path.isfile(dst):
        if not copyFile(src, dst):
            print '[Failed]'
            return
        print '[OK]'
    else:
        cfgExist = True
        print '[skipped]'

    if cfgExist:
        if not askUser('\nConfiguration file sageplex_cfg.json already exist.\n',
                       'Do you want to reconfigure its setting?'):
            return True

    # configure sageplex_cfg.json file
    if not configCfgFile(dst):
        return

    return True


def removePlexFiles(plexPath):
    '''Remove PLEX files

    @param plexPath  path to PLEX data folder
    @return          True on success
    '''
    global g_step

    # delete scanners
    dst = os.path.join(plexPath, r'Scanners/Movies')

    print '[%d] Deleting PLEX Scanners ...' % g_step,
    sys.stdout.flush()
    g_step += 1

    if not deleteFile(dst, isTree=True):
        print '[Failed]'
        return
    print '[OK]',

    dst = os.path.join(plexPath, r'Scanners/Series')

    if not deleteFile(dst, isTree=True):
        print '[Failed]'
        return
    print '[OK]'

    # copy bmt agent
    print '[%d] Deleting PLEX Agent ...' % g_step,
    sys.stdout.flush()
    g_step += 1

    dst = os.path.join(plexPath, r'Plug-ins/BMTAgentTVShows.bundle')

    if not deleteFile(dst, isTree=True):
        print '[Failed]'
        return
    print '[OK]'

    print '[%d] Deleting sageplex_cfg.json ...' % g_step,
    sys.stdout.flush()
    g_step += 1

    # setup sageplex_cfg.json file
    dst = os.path.join(plexPath, CFG_FILE)

    if not deleteFile(dst):
        print '[Failed]'
        return
    print '[OK]'

    return True


def runInstall(sagePath, plexPath):
    '''Performs an install

    @return  True on success
    '''
    # we want to print intelligent message depending on whether
    # sage/plex is both found on the machine or not.
    if sagePath and plexPath:
        progs = 'SageTV and PLEX Media Server'
    elif sagePath:
        progs = 'SageTV'
    elif plexPath:
        progs = 'PLEX Media Server'
    else:
        assert(0)

    print ''
    if not askUser('This will install SageTV for PLEX Media Server on this system.\n'
                   '%s should be stopped before you continue.\n' % progs,
                   'Do you want to continue?'):
        return

    logging.info('Performing Install actions')
    print ''

    # copy sagetv files
    if sagePath:
        if not copySageFiles(sagePath):
            return

    # copy plex files
    if plexPath:
        if not copyPlexFiles(plexPath):
            return

    # done, print some help messages at the end
    print '\nInstall completed. Please restart %s.' % progs

    if not sagePath:
        print ('\nNote: SageTV is not found on this system.\n'
               'You should run the installer again on the SageTV system to complete the setup.')
    if not plexPath:
        print ('\nNote: PLEX Media Server is not found on this system.\n'
               'You should run the installer again on the PLEX system to complete the setup.')

    return True


######################################################################
# config functions
######################################################################

def agentLogLoc(scanLog):
    '''Figure out the agent log location based on the scanner log

    @param scanlog  path to the scanner log
    @return         BMT agent log location
    '''
    logdir = os.path.dirname(scanLog)
    if isWin:
        bmtlog = r'PMS Plugin Logs\com.plexapp.agents.bmtagenttvshows.log'
    else:
        bmtlog = r'PMS Plugin Logs/com.plexapp.agents.bmtagenttvshows.log'
    return os.path.join(logdir, bmtlog)


def configCfgFile(cfg):
    '''Configures the sageplex_cfg.json file

    Read the json file, prompt user for various settings, and write
    updated setting back to json file if changed.

    @param cfg:  path to sageplex_cfg.json
    @return      True on success
    '''
    print ''
    data = None
    with open(cfg) as infile:
        data = json.load(infile)

    if not data:
        logging.error('Invalid CFG file: %s', cfg)
        print 'Invalid CFG file'
        return

    logging.info('Configuring sageplex_cfg.json')
    changed = False

    # sagex settings
    sagex = data.get('sagex')

    print 'SageTV sagex settings:'
    ans = askSettings('  host', sagex['host'])
    if ans:
        logging.info('sagex[host]: %s', ans)
        sagex['host'] = ans
        changed = True

    ans = askSettings('  port', sagex['port'])
    if ans:
        logging.info('sagex[port]: %s', ans)
        sagex['port'] = ans
        changed = True

    ans = askSettings('  username', sagex['user'])
    if ans:
        logging.info('sagex[user]: %s', ans)
        sagex['user'] = ans
        changed = True

    ans = askSettings('  password', sagex['password'])
    if ans:
        logging.info('sagex[password]: ****')
        sagex['password'] = ans
        changed = True

    # plex settings
    plex = data.get('plex')
    print 'PLEX settings:'

    ans = askSettings('  host', plex['host'])
    if ans:
        logging.info('plex[host]: ****')
        plex['host'] = ans
        changed = True

    ans = askSettings('  port', plex['port'])
    if ans:
        logging.info('plex[port]: %s', ans)
        plex['port'] = ans
        changed = True

    # finally update the scanner log location based on platform
    old_log = data['scanner']['log']
    if isWin:
        new_log = data['ignored']['log_win']
    elif isMac:
        new_log = data['ignored']['log_mac']
    elif isLin:
        new_log = data['ignored']['log_lin']

    if old_log != new_log:
        # save setting
        data['scanner']['log'] = new_log
        changed = True
        logging.info('scanner[log]: %s', new_log)

    # output scanner/agent log location
    slog = expandVarsUser(new_log)
    print 'Logs:'
    print '  scanner:', slog
    print '  agent:', agentLogLoc(slog)

    print ''
    if not changed:
        logging.info('Settings not changed.')
        print 'Settings not changed:', cfg
        return True

    # now write new setting to file
    logging.info('Saving new settings ...')
    with open(cfg, 'w') as outfile:
        json.dump(data, outfile, sort_keys=True, indent=4)

    print ('Settings saved: %s\n'
           'This can reconfigured via the -c option in the installer.' % cfg)
    return True


def runConfig(plexPath):
    '''Performs configuration of sageplex_cfg.json
    '''
    logging.info('Performing Configure actions')

    cfgPath = os.path.join(plexPath, CFG_FILE)
    if not os.path.isfile(cfgPath):
        print 'CFG file not found: ', cfgPath
        logging.error('File not found: %s', cfgPath)
        return

    configCfgFile(cfgPath)


######################################################################
# uninstall functions
######################################################################

def runUninstall(sagePath, plexPath):
    '''Performs an uninstall

    @param sagePath  SageTV path or None
    @param plexPath  PLEX data location or None
    '''
    # we want to print intelligent message depending on whether
    # sage/plex is both found on the machine or not.
    if sagePath and plexPath:
        progs = 'SageTV and PLEX Media Server'
    elif sagePath:
        progs = 'SageTV'
    elif plexPath:
        progs = 'PLEX Media Server'
    else:
        assert(0)

    if not askUser('\nThis will UNINSTALL SageTV for PLEX Media Server on this system.\n'
                   '%s should be stopped before you continue.\n' % progs,
                   'Do you want to continue?'):
        return

    logging.info('Performing Uninstall actions')
    print ''

    # copy sagetv files
    if sagePath and not removeSageFiles(sagePath):
        return

    # copy plex files
    if plexPath and not removePlexFiles(plexPath):
        return

    # done, print some help messages at the end
    print '\nUninstall completed. Please restart %s.' % progs

    if not sagePath:
        print ('\nNote: SageTV is not found on this system.\n'
               'You should run uninstall again on the SageTV system to complete the removal.')
    if not plexPath:
        print ('\nNote: PLEX Media Server is not found on this system.\n'
               'You should run uninstall again on the PLEX system to complete the removal.')

    return True


######################################################################
# main functions
######################################################################

def parseArgs():
    '''Parse command line arguments

    @return  namespace from ArgumentParser.parse_args
    '''
    # add the parent parser
    parser = argparse.ArgumentParser(epilog = PROG_DESC)

    group = parser.add_mutually_exclusive_group()

    # install
    group.add_argument('-i', '--install',
                       help='Install SageTV for PLEX on this system',
                       action='store_true')

    group.add_argument('-u', '--uninstall',
                       help='Remove SageTV for PLEX on this system',
                       action='store_true')

    group.add_argument('-c', '--config',
                       help='Configure sageplex_cfg.json file',
                       action='store_true')

    # parse the arguments
    args = parser.parse_args()
    # print args

    # do some sanity check on parameters

    # any work to do?
    if (args.install or args.uninstall or args.config):
        return args
    else:
        parser.print_help()

def setupLogging():
    '''Setup logging for the installer'''

    if isWin:
        # on windows put log in %temp%
        tmploc = os.path.expandvars('$TEMP')
        if tmploc == '$TEMP':
            tmploc = ''
    elif isLin:
        # on linux put logs in plex home folder
        tmploc = os.path.expanduser('~plex')
        if tmploc == '~plex':
            tmploc = '/tmp'

    logloc = os.path.join(tmploc, 'sageplex_install.log')
    logging.basicConfig(format=LOG_FORMAT, level=logging.DEBUG,
                        filename=logloc)
    logging.info('***** Entering SagePlex Install %s *****', sys.argv[1:])


def checkSourceFolders(rloc):
    '''Make sure we have plex/SageTV subfolders to copy files from

    @param rloc  root folder of the zip content
    @return      True if expected folders exist
    '''
    dir1 = os.path.join(rloc, 'sagetv')
    dir2 = os.path.join(rloc, 'plex')

    notFound = False
    if not os.path.isdir(dir1):
        logging.error('Dir not found: %s', dir1)
        notFound = True
    if not os.path.isdir(dir2):
        logging.error('Dir not found: %s', dir2)
        notFound = True

    if notFound:
        print 'Base location:', rloc
        print 'Required source sub-folder "plex" or "sagetv" not found!'
        return

    return True


def getRootFolder():
    '''Return the root of the zip content
    '''
    # first get script location
    loc = os.path.dirname(os.path.realpath(sys.argv[0]))

    # script loc could be x levels from root, go up until we see install.txt
    found = False
    for i in range(2): # look 2 levels up
        loc = os.path.join(loc, '..')
        f = os.path.join(loc, 'install.txt')
        if os.path.isfile(f):
            found = True
            break

    if not found:
        return

    # normalize path, collapse ../../
    loc = os.path.normpath(loc)
    logging.info('root folder: %s', loc)

    return loc


def main():
    '''Main entry point function'''
    global g_root

    # parse arguments
    args = parseArgs()
    if not args:
        return

    # if running on linux, make sure we are running as plex user
    # as the target we are copying to belongs to plex user
    if isLin:
        whoami = os.getenv('USER')
        if whoami != 'plex':
            print ("%s: please run this script as the 'plex' user.\n"
                   "This can be done via 'sudo -u plex <command>'."
                   % whoami)
            return

    # parameter is OK, initialize logs
    setupLogging()

    # figure out where the root location is
    rloc = getRootFolder()
    if not rloc:
        print 'Unable to locate base location where install.txt resides!'
        return

    # sanity check root/source folder
    if not checkSourceFolders(rloc):
        return
    g_root = rloc

    # detect sagetv/plex location
    sagePath = detectSage()
    plexPath = detectPlex()

    if (not sagePath) and (not plexPath):
        if isWin:
            print 'SageTV and PLEX not detected, abort!'
        else:
            print 'PLEX not detected, abort!'
        return

    # now do the real work
    if args.install:
        runInstall(sagePath, plexPath)
    elif args.uninstall:
        runUninstall(sagePath, plexPath)
    elif args.config:
        runConfig(plexPath)


if __name__ == '__main__':
    # detect platform
    if sys.platform == 'win32':
        import _winreg as wreg
        isWin = True
    elif sys.platform == 'darwin':
        isMac = True
    elif 'linux' in sys.platform:
        isLin = True
    else:
        print 'Unknown platform: ', sys.platform
        sys.exit(1)
    # do work
    sys.exit(main())
