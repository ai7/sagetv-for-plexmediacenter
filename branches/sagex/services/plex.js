/*
* Name: GetMediaFileForName
* Author: PiX64 (reid, michael)
*
* Parms: a filename such as Myshow.mkv
* Return: false if no mediafile found with given name
*         Mediafile object: if a mediafile found with given name
* Purpose: given a filename, will grab all mediafiles from sage, and loop through trying to find a
*  mediafile match for the given name
* 
**********************/
function GetMediaFileForName(filename) {
	var allMedia = MediaFileAPI.GetMediaFiles();
	
	//var allMedia = SageAPI.call('GetMediaFiles', null);
	
	//var allMedia = SageAPI.call("DataUnion", [SageAPI.call("GetMediaFiles", ["T"]), SageAPI.call("GetMediaFiles", ["TL"])]);
	//var allMedia = SageAPI.call("GetMediaFiles", ["TL"]);
	var mediaFile= false;
	
	//
	// Loop through all media objects returned by GetMediaFiles in order to try and find a match
	// in the relative path OR in the SegmentFiles
	//
	for (i=0; i < allMedia.length; i++){
		//Get relative path
		mediaFilename = MediaFileAPI.GetMediaFileRelativePath(allMedia[i]);
		
		//
		// If mediaFilename returned by GetMediaFileRelativePath matches the parameter filename passed in
		// then we want to return the currrent media object we are inspecting.
		//
		if (mediaFilename == filename){
			mediaFile = allMedia[i];
			continue;
		}
		
		//
		// If no result found in relative path above, then we need to search subfiles
		//
		var subfiles = MediaFileAPI.GetSegmentFiles(allMedia[i]);
      	//for each subfile returned from GetSegmentFiles look for a match in the filename
      	for (n=0;n<subfiles.length;n++) {
           //If we find a match by checking that the aboslute path contains our filename, return media object to caller
           if (subfiles[n].getAbsolutePath().contains(filename)) {
               mediaFile = allMedia[i];
               continue;
           }
        }
		
	}
		
	return mediaFile;
	
}