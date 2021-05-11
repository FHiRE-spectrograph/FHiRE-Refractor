import sys, picamera
from pydng.core import RPICAM2DNG
from cr2fits import cr2fits
from time import sleep
from fractions import Fraction

class Refractor():
	def __init__(self):
		super().__init__()

	def take_exposure(self,expTime):
		fname = 'RefractorImage_temp'
		time = int(expTime)*1000000 #time in microSec

		# taking img with picamera (max exposure time for HQ cam is 200s)
		#TO DO: Test camera settings when at WIRO. use for dark exposures? 
		#self.camera = picamera.PiCamera(framerate=Fraction(1, 6),sensor_mode=3)
		self.camera = picamera.PiCamera()		
		self.camera.iso = 800
		#self.camera.brightness = 80
		#self.camera.contrast = 100
		# give camera time to set gains and measure AWB (might want to use fixed AWB instead)
		sleep(2)
		self.camera.shutter_speed = time
		self.camera.exposure_mode = 'off'
		# fixes white balance gains (AWB). dont know if it is necessary
		g = self.camera.awb_gains
		self.camera.awb_mode = 'off'
		self.camera.awb_gains = g
		self.camera.capture(fname+".jpg", format='jpeg', bayer=True)

		self.convert2fits(fname)

	# converts to a raw image (dng), then converts raw to fits
	def convert2fits(self,img):
		img_jpg = img + '.jpg'
		rawConvert = RPICAM2DNG()
		rawConvert.convert(img_jpg)

		img_raw = img + '.dng'
		img_fits = img + '.fits'
		# color-index can take one of four values, either 0, 1, 2, 3 which represent Red, Green, Blue and Unscaled Raw respectively
		fitsConvert = cr2fits(img_raw, 1)
		fitsConvert.convert()

if __name__ == '__main__': 
	refract = Refractor()
	refract.take_exposure(sys.argv[1])
