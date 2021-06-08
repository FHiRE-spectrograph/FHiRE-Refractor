import sys, picamera, os
from pydng.core import RPICAM2DNG
from cr2fits import cr2fits
from time import sleep
from fractions import Fraction

class Refractor():
	def __init__(self):
		super().__init__()

		#_stderr = sys.stderr
		#_stdout = sys.stdout
		#null = open(os.devnull, 'wb')
		#sys.stderr = sys.stdout = null

	def take_exposure(self, expTime):
		fname = 'RefractorImage_temp'
		time = int(expTime) * 1000000  # time in microSec

		# Taking img with picamera (max exposure time for HQ 
		# cam is 200s).
		# TO DO: Test camera settings when at WIRO. Use for 
		# dark exposures? 
		#self.camera = picamera.PiCamera(
		#	framerate=Fraction(1, 6), sensor_mode=3)

		self.camera = picamera.PiCamera()		
		self.camera.iso = 800
		#self.camera.brightness = 80
		#self.camera.contrast = 100
		# Give camera time to set gains and measure AWB 
		# (might want to use fixed AWB instead).
		sleep(2)
		self.camera.shutter_speed = time
		self.camera.exposure_mode = 'off'
		# Fixes white balance gains (AWB). Dont know if it 
		# is necessary.
		g = self.camera.awb_gains
		self.camera.awb_mode = 'off'
		self.camera.awb_gains = g
		self.camera.capture(fname + ".jpg", format='jpeg', bayer=True)

		print("Exposure complete.")

		self.convert2fits(fname)

	# Converts to a raw image (dng), then converts raw to fits.
	def convert2fits(self,img):
	
		print("Converting to fits.")
		
		img_jpg = img + '.jpg'
		rawConvert = RPICAM2DNG()
		rawConvert.convert(img_jpg)

		img_raw = img + '.dng'
		img_fits = img + '.fits'
		# color-index can take one of four values, either 0, 1, 
		# 2, 3. Represent Red, Green, Blue and Unscaled 
		# Raw respectively.
		fitsConvert = cr2fits(img_raw, 1)
		fitsConvert.convert()
		
		print("Conversion complete.")

if __name__ == '__main__': 
	refract = Refractor()
	refract.take_exposure(sys.argv[1])
