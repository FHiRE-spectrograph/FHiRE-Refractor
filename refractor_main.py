#
# Important: Run using python3
#
from PyQt5 import QtCore,QtWidgets
try:
	import sys,time,os,threading,queue,fnmatch,subprocess,pyds9
except ImportError:
	print("* Need to run refractor_main.py using python3.")
	sys.exit()
import numpy as np
import RPi.GPIO as GPIO
from astropy.io import fits
from Centroid_DS9 import imexcentroid
import refractorGUI

# Set terminal output to GUI textBox.
class EmittingStream(QtCore.QObject):
	textWritten = QtCore.pyqtSignal(str) 
	def write(self, text):
		self.textWritten.emit(str(text))
	def flush(self):
		pass

# Refractor cover microswitch control class.
class switch(object):
	def __init__(self, pin_out=0, pin_in=0, name='switch'):
		self.pin_out = pin_out
		self.pin_in = pin_in
		GPIO.setmode(GPIO.BCM)
		GPIO.setwarnings(False)

		# Check that pins have been defined & setup input/output.
		# 3.3k resistors added to output to protect against the
		# microswitch shorting GPIO pins.
		if self.pin_out == 20:
			GPIO.setup(self.pin_out, GPIO.OUT)
			GPIO.output(self.pin_out, 0)

		if self.pin_in == 19:
			GPIO.setup(
				self.pin_in,
				GPIO.IN, 
				pull_up_down=GPIO.PUD_DOWN) 

	def pin_start(self):
		GPIO.output(self.pin_out, 1)

	def pin_stop(self):
		GPIO.output(self.pin_out, 0)

# class that controls the refractor cover stepper motor via the 
# stepper driver board.
class microStepDriver(QtCore.QObject):
	def __init__(self, parent=None):
		super(self.__class__, self).__init__(parent)

		# Stepper Drive Pulses (RPi pin #11).
		self.PUL = 17  
		# Controller Direction Bit (High for default/Low for 
		# reverse) (RPi pin #13).
		self.DIR = 27  
		# Controller Enable Bit (High to enable/Low to disable)
		# (RPi pin #15).
		self.ENA = 22  
		# 800/2 pulse/rev * 27 (gear ratio) for 180 deg rotation.
		self.duration = 10800 
		# Delay between PUL pulses - effectively sets the 
		# motor rotation speed.
		self.delay = 0.0001 
		self.gearRatio = 26.8512397
		self.stepAngle = 1.8  # degrees
		self.microStep = 4  # which means 800 pulse/rev
		self.motorPosition = 0

		# Set GPIO pins and outputs.
		GPIO.setmode(GPIO.BCM)
		GPIO.setwarnings(False)
		GPIO.setup(self.PUL, GPIO.OUT)
		GPIO.setup(self.DIR, GPIO.OUT)
		GPIO.setup(self.ENA, GPIO.OUT)

		# Disable stepper motor to prevent idle current.
		self.disable()
	
	# Stepper motor commands.
	def enable(self):
		GPIO.output(self.ENA, GPIO.LOW)

	def disable(self):
		GPIO.output(self.ENA, GPIO.HIGH)

	def forward(self):
		GPIO.output(self.DIR, GPIO.HIGH)

	def reverse(self):
		GPIO.output(self.DIR, GPIO.LOW)

	def go(self):
		GPIO.output(self.PUL, GPIO.LOW)

	def stop(self):
		GPIO.output(self.PUL, GPIO.HIGH)

	def drive(self):
		self.go()
		time.sleep(self.delay)
		self.stop()
		time.sleep(self.delay)

	def open_cover(self):
		self.enable()
		time.sleep(.5)  # pause for possible change direction
		self.forward()
		for x in range(self.duration):
			self.drive()
			self.motorPosition += 1
		self.disable()
		time.sleep(.5)  # pause for possible change direction
		print('> Cover open - Motor at position %s' %
						self.motorPosition)
		return

	def close_cover(self):
		self.enable()
		time.sleep(.5)
		self.reverse()
		for y in range(self.duration):
			self.drive()
			self.motorPosition -= 1
		self.disable()
		time.sleep(.5)
		print('> Cover closed - Motor at position %s' %
						self.motorPosition)
		return

	def close(self):
		GPIO.cleanup()

# Main GUI class. Inherits layout from refractorGUI.
class MainUiClass(QtWidgets.QMainWindow, refractorGUI.Ui_MainWindow):
	def __init__(self, parent=None):
		super(MainUiClass, self).__init__(parent)
		self.setupUi(self)
		
		# Initiate cover microswitch and stepper motor classes.
		self.switch = switch(20,19)  # microswitch out, in
		self.motor = microStepDriver()
		
		# Make sure cover is closed at the home postion.
		self.cover_home() 

		# Set regions.reg filepath.
		self.regionpath = '/home/fhire/Desktop/FHiRE-Refractor/ \
								regions.reg'
	
		# Start threads and connect GUI buttons.
		self.createThreads()
		self.connectButtons()

		# Send terminal output to textBox.
		sys.stdout=EmittingStream(textWritten=self.normalOutputWritten)
		# Comment out to send errors to terminal instead of textBox.
		#sys.stderr=EmittingStream(
		#		textWritten=self.normalOutputWritten)
		print("> Refractor cover sent home.")

	# Set up threads.
	def createThreads(self):
		# Start queue thread.
		self.q = queue.Queue()
		self.queueThread()

		######## TEST WHEN UP THE MOUNTAIN ######
		# Start Claudius thread.
		#self.claudiusthread = Claudius() 
		#self.claudiusthread.start()
		#self.claudiusthread.signal.connect(self.setClaudiuslnk)
		#print('Threads are connected.')

	# Connect buttons to functions.
	def connectButtons(self):
		self.closeButton.setChecked(True)
		self.openButton.clicked.connect(
				lambda:	self.q.put(self.coverState))
		self.openButton.setToolTip("Opens the refractor" \
					   "telescope cover.")

		self.closeButton.clicked.connect(
				lambda: self.q.put(self.coverState))
		self.closeButton.setToolTip("Closes the refractor" \
			 		    "telescope cover.")

		self.exposeButton.pressed.connect(
				lambda: self.q.put(self.refractor_exp))
		self.exposeButton.setToolTip("Takes exposures and saves " \
					     "temporary FITS image to " \
					     "~/Desktop/Images.")

		self.ds9Button.clicked.connect(
				lambda: self.q.put(self.openDS9))
		self.ds9Button.setToolTip("Opens a new ds9 window.")

		self.centroidButton.clicked.connect(lambda: self.preCentroid())
		self.centroidButton.setToolTip("Centroids on a star and " \
					       "sends offsets to Claudius.\n" \
					       "Set a box region around " \
					       "desired star in DS9 first.")

		# Set default time and number of exposures and call 
		# update function.
		self.numberExp.setValue(1)
		self.timeExp.setValue(1)
		self.numberExp.valueChanged.connect(self.updateExp)
		self.numberExp.setToolTip("Sets the number of exposures " \
					  "to take with the refractor guide " \
					  "camera.\nExposures will be " \
					  "stacked upon completion.")
		self.timeExp.valueChanged.connect(self.updateExp)
		self.timeExp.setToolTip("Sets the length of exposures " \
					"in seconds.")
		self.updateExp()
		#print ('Buttons are connected.')

	# Runner that performs tasks in queue in order.
	# This way multiple functions aren't called at once and the 
	# GUI doesnt freeze up.
	def queueRunner(self):
		while True:
			f = self.q.get()
			f()
			self.q.task_done()

	# Thread that runs the queue.
	def queueThread(self):
		queueWorker = threading.Thread(target=self.queueRunner)
		# Daemon thread will close when application is closed.
		queueWorker.setDaemon(True)
		queueWorker.start()

	# Updates the number and length of exposures when spin wheels
	# are changed.
	def updateExp(self):
		self.num_exp = self.numberExp.value()
		self.time_exp = self.timeExp.value()

	# Connects to Claudius ssh from Claudius thread.
	def setClaudiuslnk(self,lnk):
		self.claudiuslnk = lnk

	# Calls motor to open or close cover when radio button is changed.
	def coverState(self):
		if self.openButton.isChecked() == True:
			print ("> Opening cover...")
			self.motor.open_cover()
				
		elif self.closeButton.isChecked() == True:
			print ("> Closing cover...")
			self.motor.close_cover()

	# Finds files in a folder.
	def find(self, pattern, path):
		result = []
		for root, dirs, files in os.walk(path):
			for name in files:
				if fnmatch.fnmatch(name, pattern):
					result.append(os.path.join(root, name))
		return result
	#
	# Takes exposures, converts to FITS file and saves path to 
	# guiding image. Conversion to FITS file requires python3.7 
	# so have to call the script from terminal.
	#
	def refractor_exp(self):		
		# Delete any old images.
		old_images = self.find('RefractorImage*', 
				       '/home/fhire/Desktop/FHiRE-Refractor')
		if old_images:
			os.system("rm RefractorImage_temp*")
		else:
			pass

		# Read the number and time exp spin boxes and take
		# that many images. Conversion to fits takes longer
		# than exposure and happens immediately for each exposure.
		#print("> Please wait for exposure(s) and conversion.")
		for x in range(0, self.num_exp):
	
			print("> Taking %s of %s exposure(s)..." %(
						x+1, self.num_exp))

			proc = subprocess.Popen(["python3.7", 
					         "refractor_camera.py", 
					         str(self.time_exp)])
			proc.wait()  
			(stdout, stderr) = proc.communicate()
		
			#if proc.returncode != 0:
			#	print("> ERROR: Camera not connected.")
			#	return

			print("> Exposure %s of %s complete and converted." %(
							   x+1, self.num_exp))
		
		# If more than one exposure stack images.
		if self.num_exp > 1:
			image_list = self.find(
					'*.fits', 
					'/home/fhire/Desktop/FHiRE-Refractor')
			image_concat = [fits.getdata(image) for image in image_list]
			final_image = np.sum(image_concat, axis=0)

			outfile = 'RefractorImage_temp-stacked.fits'
			hdu = fits.PrimaryHDU(final_image)
			hdu.writeto(outfile, overwrite=True)
			self.imgpath = "/home/fhire/Desktop/FHiRE-Refractor" \
				       "/RefractorImage_temp" \
				       "-stacked.fits"
			self.img = 'RefractorImage_temp-stacked.fits'
			print ("> Exposure stack saved to %s" %self.imgpath)
			self.openDS9(True)

		# Otherwise, don't stack.
		else:
			self.imgpath = "/home/fhire/Desktop/FHiRE-Refractor" \
				       "/RefractorImage_temp-G.fits"
			self.img = 'RefractorImage_temp-G.fits'
			print ("> Exposure saved to %s." %self.imgpath)
			self.openDS9(True)

	# Opens DS9 and shows last exposure if it exists.
	def openDS9(self, image=False):
		if image == False:
			print("> Opening ds9...")			
		# Opens DS9 or points to existing window if already open.
		pyds9.DS9()
		# If called after taking an exposure open that exposure.
		if image == True:
			print("> Opening image in ds9...")
			os.system('xpaset -p ds9 fits ' + str(self.imgpath))
			os.system('xpaset -p ds9 zoom to fit')
			os.system('xpaset -p ds9 zscale')
		elif image == False:
			print("> ds9 opened.")

	# Closes cover until home switch is triggered. Called at 
	# beginning and end of GUI.
	def cover_home(self):
		print("> Sending refractor cover home.")
		self.motor.enable()
		self.motor.reverse()
		time.sleep(.5)  # pause for possible change direction
		self.switch.pin_start()
		time.sleep(0.05)
		if GPIO.input(19) == 1:  # if not at home send home
			while GPIO.input(19) == 1:
				self.motor.drive()
		self.switch.pin_stop()
		print("> Refractor cover sent home.")
		self.motor.disable()
	
	# Centroiding method.
	def mycen(self):
		# Temporary path for testing.
		#self.imgpath='/home/fhire/Desktop/Refractor/GAMimage.fit' 
		try:
			### TO DO: Set position of the optical fiber ###
			subprocess.run(["xpaset", 
					"-p", 
					"ds9", 
					"regions", 
					"command", 
					"{point 2000 1700 # point=x " \
							"20 color=red}"], 
								check=True)
		
			# Save current ds9 regions to reg file and 
			# then read and compute centroid.
			subprocess.run(["xpaset", 
					"-p", 
					"ds9", 
					"regions", 
					"save", self.regionpath], 
							check=True)

			try:
				[xcenter, ycenter] = imexcentroid(
							self.imgpath, 
							self.regionpath)
			except:
				print("> ERROR: Image not found.")

			# Compute the offset and display.
			### TO DO: Set position of the optical fiber ###
			xdiff = xcenter - 2000
			ydiff = ycenter - 1700

			### TO DO: check direction of camera vs telescope
			# and set image scale ###
			if xdiff < 0:
				xoffset = "nn %s" %abs(.057 * xdiff)
			elif xdiff >= 0:
				xoffset = "ss %s" %(.057 * xdiff)
			if ydiff < 0:
				yoffset = "ee %s" %abs(.057 * ydiff)
			elif ydiff >= 0:
				yoffset = "ww %s" %(.057 * ydiff)	
		
			print("(%s, %s)" %(xcenter, ycenter))
			print("%s %s" %(xoffset, yoffset))

			move_offset = (xoffset + ";" + yoffset)

			### TO DO: TEST WHEN UP THE MOUNTAIN ###
			# send offset command to Claudius
			#print("<span style=\"color:#0000ff;\">" \
			#      "<b>observer@claudius: </b>" + " \
			#      "move_offset + "</span>")
			#self.claudiuslnk.sendline(move_offset)
			#self.claudiuslnk.prompt()
			#print("<span style=\"color:#0000ff;\">" + " \
			#      "self.claudiuslnk.before + "</span>")

		# Catch errors if DS9 not open, there is no region in
		# DS9, or no exposure.
		except subprocess.CalledProcessError:
			print ('> ERROR: Cannot find image in DS9.')
		except AttributeError:
			print ("> ERROR: No exposure found. Take an " \
			       "exposure with the refractor guiding camera.")
		except ValueError:
			print ("> ERROR: No region found in DS9. Draw a " \
			       "box region around a star to centroid.")

	# Centroid warning message to set region in DS9.
	def preCentroid(self):
		msg = QtWidgets.QMessageBox.information(
					self,
					"DS9 Reminder",
					"Is DS9 open? Is there a box " \
						"region around a star to " \
						"guide on?\nNote: Can only " \
						"centroid on last exposed " \
						"refractor image.", 
					QtWidgets.QMessageBox.No|\
						QtWidgets.QMessageBox.Yes, 
					QtWidgets.QMessageBox.No)
		if msg == QtWidgets.QMessageBox.Yes:
			print("> Beginning offset.")
			self.q.put(self.mycen)

		elif msg == QtWidgets.QMessageBox.No:
			print('Offset canceled.')
			pass

	# Gives warning window before closing the GUI.
	def closeEvent(self, event):
		reply = QtWidgets.QMessageBox.question(
					self,
					"Window Close",
					"Are you sure you want to close " \
						"the window? This will " \
						"close the refractor " \
						"telescope cover.",
					QtWidgets.QMessageBox.Yes|\
						QtWidgets.QMessageBox.No, 
					QtWidgets.QMessageBox.No)
		if reply == QtWidgets.QMessageBox.Yes:
			print("Wait while refractor cover closes.")
			event.accept()
			#self.claudiuslnk.logout() 
			self.cover_home()
			self.motor.close()
			print("Window Closed.")
		else:
			event.ignore()

	# Restores sys.stdout and sys.stderr.
	def __del__(self):
		sys.stdout=sys.__stdout__
		sys.stderr=sys.__stderr__
		
	# Writes terminal output to textEdit.
	def normalOutputWritten(self,text):		
		self.textEdit.insertPlainText(text)
		# Set scroll bar to focus on new text.
		sb = self.textEdit.verticalScrollBar()
		sb.setValue(sb.maximum())

# Claudius communication thread.
class Claudius(QtCore.QThread):
	signal = QtCore.pyqtSignal('PyQt_PyObject')

	def __init__(self, parent=None):
		super(Claudius, self).__init__(parent)
	def run(self):
		time.sleep(1)
		start = time.time()
		lnk = pxssh.pxssh()
		hostname = '10.214.214.110'
		username = 'observer'
		password = 'iii2skY'
		lnk.login(hostname, username, password)
		self.signal.emit(lnk)
		end = time.time()
		print('Claudius connected. Time elapsed: %.2f seconds' %(
								end - start))

	def stop(self):
		self.terminate()

#Start/Run GUI window.
if __name__ == '__main__':
	app = QtWidgets.QApplication(sys.argv)
	GUI = MainUiClass()
	GUI.show()
	app.exec_()


#Use camera from command line for constant feed
#raspivid -f -k

