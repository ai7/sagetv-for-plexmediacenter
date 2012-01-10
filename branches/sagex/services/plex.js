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
	allMedia = SageAPI.call('GetMediaFiles', null);
	mediaFile= false;
	
	for (i=0; i < allMedia.length; i++){
		mediaFilename = MediaFileAPI.GetMediaFileRelativePath(allMedia[i]);
		if (mediaFilename == filename){
			mediaFile = allMedia[i];
			continue;
		}
	}
	
	return mediaFile;
}