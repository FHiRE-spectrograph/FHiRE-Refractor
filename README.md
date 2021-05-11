# Refractor Telescope Guiding Camera
## Updated: 3-5-21
### Contact: Jason Rothenberg (jrothenb@uwyo.edu)

*Scripts posted to GITHUB
__bold__ Important (Core) scripts.

## Overview  :

This script controls the refractor telescope guiding camera. It is intended to automate the initial pointing of the WIRO telescope. First 'Open' the refractor cover. After moving to a source, take an exposure with the guide camera. Open that exposure in DS9 and place a region around the target star in the image. To select a region in DS9 set Region>Shape>Box, then click Edit>Region, and finally drag a box around a target star. Once a star is selected, press the 'Centroid and offset' button to calculate the distance from the centroid of the star to the FHiRE optical fiber (or center of another instrument) and automatically move the telescope. The script closes the refractor cover when the GUI is closed. To run the GUI type 'python3 refractor_main.py' in the terminal.  

## List of files:

__*refractor_main.py__:  
	Main code that controls thr refractor telescope camera and refractor cover. To run the refractor camera GUi run with python3 in a terminal window.  

*refractor.ui:  
	GUI design made with PyQt5 designer.  

__*refractorGUI.py__:  
	Imported into refractor_main.py to set GUI layout. Created with Qt5 Designer. Converted from refractor.ui via the command 'pyuic5 refractor.ui -o refractorGUI.py'.   

### Converting raw to fits:

__*refractor_camera.py__:  
	Script that takes images with the RPi HQ camera and converts from jpg to fits. Depends on GitHub modules cr2fits and pydng to do the fiel conversion. Requires python3.7 to run.  

__*cr2fits.py__:  
	Converts RAW Camera images to FITS. Details at https://github.com/eaydin/cr2fits.  

__*cr2fits__:  
	Folder containing files from https://github.com/eaydin/cr2fits. Used to convert RAW images to FITS files.  

__*PyDNG__:  
	Folder containing files from https://github.com/schoolpost/PyDNG. Used to convert Bayer RAW Data from the RPi HQ camera to RAW DNG images.  

__*dcraw__:  
	Also downloaded from https://github.com/eaydin/cr2fits. cr2fits depends on to convert RAW images.  

### Centroiding:

__*Centroid_DS9.py__:  
	Calculates the centroid of a source in DS9. Code by Mihai Cara and Lia Eggleston.  

__*ReadRegions.py__:  
	Save DS9 region information and outputs it to regions.reg.  

__*regions.reg__:  
	Saved DS9 region output, used to centroid and calculate telescope offsets.  

## Other folders:

records:  
	Has an old test version of the GUI (testGUI) that runs using test GAM images and doesn't communicate with Claudius. Now obsolete. refractor_centroid.py, refractor_motor.py, and refractor_switch.py have classes that centroid, control the refractor cover stepper motor, and control the refractor cover home switch respectively. Their classes were copied over into refractor_main.py so the scripts aren't currently used. Could be useful for controling the refractor guide camera and cover from the GAM.  

refractor_motor_test.py has an initial test script to control the refractor cover stepper motor.  


