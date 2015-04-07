# testing various sagex apis
#
# Run with
#   python test_sageplex.py <media_file>
# Will output data returned from sagex
#
import sys, logging, pprint

from sageplex import plexlog, config, sagex

def main():
    if len(sys.argv) < 2:
        print 'Usage: <media_file>'
        return

    logging.basicConfig(format='%(asctime)s| %(levelname)-8s| %(message)s',
                        level=logging.DEBUG)
    c = config.Config(sys.platform)
    sageapi = sagex.SageX(c.getSagexHost())

    # test various APIs
    a = sys.argv[1]
    sageapi.log.info('********** getMediaFileForName(%s) **********', a)
    mf = sageapi.getMediaFileForName(a)
    pprint.pprint(mf)
    if not mf:
        return

    a = mf['Airing']['Show']['ShowExternalID']
    sageapi.log.info('********** getShowSeriesInfo(%s) **********', a)
    r = sageapi.getShowSeriesInfo(a)
    pprint.pprint(r)

    a = mf['MediaTitle']
    sageapi.log.info('********** getMediaFilesForShow(%s) **********', a)
    r = sageapi.getMediaFilesForShow(a)
    for f in r:
        sageapi.log.info(f['SegmentFiles'])

    a = mf['MediaFileID']
    sageapi.log.info('********** getMediaFileForID(%s) **********', a)
    r = sageapi.getMediaFileForID(a)
    sageapi.log.info(r['SegmentFiles'])

if __name__ == '__main__':
    main()
