/*
 * Name:         GetMediaFileForName
 * Contributors: PiX64 (reid, michael)
 *               Raymond Chi
 *
 * This file implements a custom 'plex' service for Remote HTTP API in
 * SageTV, enabled via sagex-services and Jetty Web Server plugin.
 *
 * The service implements the API 'GetMediaFileForName'. This is
 * called by the Plex scanner from the python side through sagex's web
 * interface. 
 *
 * The purpose of the function is to return a SageTV MediaFile object
 * with all SageTV attributes based on a filename.
 *
 * The API can be tested with a browser using a link such as:
 *   http://usr:pwd@host:port/sagex/api?c=plex:GetMediaFileForName&1=file&encoder=json
 * replace 'file' with the actual filename
 *
 * SageTV API:
 *   http://download.sage.tv/api/
 * sagex-services:
 *   http://code.google.com/p/customsagetv/wiki/SageTVapi
 * RemoteHttpApiForSageTV
 *   http://code.google.com/p/customsagetv/wiki/RemoteHttpApiForSageTV
 */


/**
 * Return SageTV MediaFile obj based on filename
 *
 * Given a filename, will grab all mediafiles from sage, and loop
 * through trying to find a mediafile match for the given name
 *
 * @param filename  a filename such as Myshow.mkv
 * @return          false if no mediafile found with given name Mediafile.
 *                  object if a mediafile found with given name.
 */
function GetMediaFileForName(filename)
{
    var allMedia = MediaFileAPI.GetMediaFiles();

    // var allMedia = SageAPI.call('GetMediaFiles', null);

    // var allMedia = SageAPI.call("DataUnion", [SageAPI.call("GetMediaFiles", ["T"]),
    //                                           SageAPI.call("GetMediaFiles", ["TL"])]);
    // var allMedia = SageAPI.call("GetMediaFiles", ["TL"]);
    var mediaFile= false;

    // Loop through all media objects returned by GetMediaFiles in
    // order to try and find a match in the relative path OR in the
    // SegmentFiles
    for (i = 0; i < allMedia.length && !mediaFile; i++) {

        // Get relative path
        mediaFilename = MediaFileAPI.GetMediaFileRelativePath(allMedia[i]);

        // If mediaFilename returned by GetMediaFileRelativePath
        // matches the parameter filename passed in then we want to
        // return the currrent media object we are inspecting.
        if (mediaFilename === filename) {
	    mediaFile = allMedia[i];
            break; // break out of main loop
        }

        // If no result found in relative path above, then we need to
        // search subfiles
        var subfiles = MediaFileAPI.GetSegmentFiles(allMedia[i]);
        // for each subfile returned from GetSegmentFiles look for a
        // match in the filename
        for (j = 0; j < subfiles.length; j++) {
            // If we find a match by checking that the aboslute path
            // contains our filename, return media object to caller
            var segf = subfiles[j];
            // occasionally subfiles[j] is 'undefined' as shown in
            // com.plexapp.agents.bmtagenttvshows.log, so we add check
            // here as otherwise we'll get an exception
            if (segf && segf.getAbsolutePath().contains(filename)) {
                mediaFile = allMedia[i];
                // inner loop, main loop will end also due to
                // mediaFile
                break;
            }
        }
    }

    return mediaFile;
}


// Useful stuff:
//
//   JavaScript truthy values: false/null/undefined/''/0/NaN
//
// Open question:
//
//   Q1: where to output logs?
//
//   Q2: would it be faster if we simply return all of
//       MediaFileAPI.GetMediaFiles() to python and do all the
//       repeated searches for different files there?
