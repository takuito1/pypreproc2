# Taku Ito
# 05/30/2014
# Creates config file to get correct inputs for execution nodes

import os
import yaml
import copy

class Config():
	"""
	Creates a configuration object (that writes to a .conf file) containing all necessary data parameters.
	Each parameter has its own attribute, with the value of the attribute being the parameter.
	"""
	# initialize empty parameters
	def __init__(self, config=None):
		# Either initialize the config object's attributes to None, or input a config file and update/re-update this config object's attributes.
		if config==None:
			self.basedir = None
			self.scriptsDir = None
			self.atlasDir = None
			self.AFNIDir = None
			self.FSDir = None
			self.numRuns = None
			self.numTRs = None
			self.TR_length = None
			self.smoothingParam = None
			self.tpattern = None
			self.listOfSubjs = None
			self.analysisName = None
			self.rawDataDir = None
			self.timingFiles = None
			self.t1_image = None
			self.epi_series = None
			self.confName = None
			self.fs_input = 'aseg.mgz'
			# subject Directories...: *************** should we instantiate them here?
			self.subjDir = self.basedir + '/%s/'
			self.subjfMRIDir = self.subjDir + '/fMRI/'
			self.subj
		else:
			parameters = yaml.load(open(config,'r'))
			for key in parameters:
				setattr(self, key, parameters[key])
				if key == 'epi_series':
					self.numRuns = len(parameters[key])

			# Handle this variable instantiation internally
		        if 'nextInputFilename' in parameters.keys():
                            pass
                        else:
                            self.nextInputFilename = ['']
					

	# Anything below this comment (within this Config class) is still in development.  Eventually I would lie to reach the point where we can set all the parameters through a prompt from the console, but this is of lower priority.

	def getBaseDir(self):
		string = raw_input('Give your base output directory: ')
		string = string.strip()
		self.basedir = string

	def getScriptsDir(self):
		string = raw_input('Give the scripts directory [default: basedir/scripts/]: ')
		string = string if string else self.baseDir + '/scripts/'
		string = string.strip()
		self.scriptsDir = string

	def getAtlasDir(self):
		string = raw_input('Give the directory containing all atlases (anatomical and functional [default: /Applications/afni/]: ')
		string = string if string else '/Applications/afni/'
		string = string.strip()
		self.atlasDir = string

	def getAFNIdir(self):
		string = raw_input('Give the directory containing AFNI [default: /Applications/afni/afni]: ')
		string = string if string else '/Applications/afni/afni'
		string = string.strip()
		self.AFNIdir = string

	def getFS_loc(self):
		string = raw_input('Give the directory containing Freesurfer [default: /Applications/freesurfer/bin/freesurfer]: ')
		string = string if string else '/Applications/freesurfer/bin/freesurfer'
		string = string.strip()
		self.FSdir = string

	def getDataParams(self):
		numRuns = raw_input('How many runs per subject?: ')
		numRuns = int(numRuns.strip())
		self.numRuns = numRuns

		numTRs = raw_input('How many TRs per run?: ')
		numTRs = int(numTRs.strip())
		self.numTRs = numTRs

		TR_length = raw_input('How long is each TR (in seconds, just input number): ')
		TR_length = TR_length.strip()
		TR_length = TR_length + 's'
		self.TR_length = TR_length

		smoothingParam = raw_input('What should the smoothing parameter be (FWHM), in mm: ')
		smoothingParam = int(smoothingParam.strip())
		self.smoothingParam = smoothingParam

		tpattern = raw_input('Input the slice acquisition order. For Siemens Trio (standard EPI sequence), alt+z when you have an odd number of slices, alt+z2 when you have an even number of slices: ')
		tpattern = tpattern.strip()
		self.tpattern = tpattern

	def getSubjects(self):
		listOfSubjs = raw_input('Input the subject IDs, delimited by commas: ')
		listOfSubjs = listOfSubjs.strip()
		listOfSubjs = listOfSubjs.split(',')
		self.listOfSubjs = listOfSubjs

	def getAnalysisName(self):
		analysisName = raw_input('What is the name of this project called: ')
		analysisName = analysisName.strip()
		self.analysisName = analysisName

	def getRawDataDir(self):
		print 'Input the raw data for each subject:'
		print "Note, indicate subject number by '%s'"
		print "For example, if you have subjects 401 and 402, and their raw data directory is: /projects/preprocessingDir/rawdata/401/, and /projects/preprocessingDir/rwadata/402/, you would indicate this by inputting '/projects/preprocessingDir/rawdata/%s' "
		string = raw_input("Give the directory of the raw data for each subject: ")
		string = string.strip()
		self.rawDataDir = string
		# Note to self, when constructing a subject's raw data directory, remember that self.rawDataDir is a 2 element list

	def getTimingFiles(self):
		string = raw_input("If applicable, give the stimulus timing files. Note, all timing files for all subjects should be in the same directory. Enter nothing if not applicable: ")
		string = string.strip()
		self.timingFiles = string

	def rawDataParams(self):
		sampleSubj = self.listOfSubjs[0]
		findRawDataDir = self.rawDataDir.split('%s')
		sampleRawData = findRawDataDir[0] + sampleSubj + findRawDataDir[1]
		rawDataContents = os.listdir(sampleRawData)
		rawDataContents = dict(enumerate(rawDataContents))
		for key,value in zip(rawDataContents.keys(), rawDataContents.values()):
			print key, ':', value

		t1_image = raw_input('Indicate the directory (by the number to its left) which directory holds the T1, anatomical scan: ')
		t1_image = rawDataContents[int(t1_image)] #get the true value
		self.t1_image = t1_image

		epi_series = raw_input('Indicate the directories (by the number to its left), which directories holds the EPI/BOLD scans IN SEQUENTIAL ORDER.  The order you input them now is the order they will be concatenated as in the future preprocessing.  Separate the numbers by a "," and no spaces in between commas (e.g., "1,2,3,4)": ')
		epi_series = epi_series.strip()
		epi_series = epi_series.split(',')
		i=0
		for key in epi_series:
			key = int(key)
			epi_series[i] = rawDataContents[key]
			i += 1

		self.epi_series = epi_series # returns a list of all BOLD scan directory names 


	def generateConfFile(self):
		string = raw_input('Give the name of your configuration file: ')
		string = string if string else "default.yaml"
		string = string if (len(string) > 5 and string[-5:] == ".yaml") else string + ".yaml"
	    # Make sure that file doesn't already exist
		if os.path.exists(string):
			print "File already exists."
			return
		else:
			self.confName = string

		newtext = open(self.confName, 'w')
		with open(self.confName, 'w') as outfile:
			outfile.write( yaml.dump(data, default_flow_style=True) )

	def run(self):
		# gather all inputs (run all methods)
		self.getBaseDir()
		self.getScriptsDir()
		self.getAtlasDir()
		self.getAFNIdir()
		self.getFS_loc()
		self.getDataParams()
		self.getSubjects()
		self.getAnalysisName()
		self.getRawDataDir()
		self.getTimingFiles()
		self.rawDataParams()
		self.generateConfFile()

		print 'Configuration file complete.  Writing to file in current working directory, titled:', self.name
		print 'All outputs will be '

	def setDefaults(self):
		"""
		Will output a default config file, most parameters will be set to None
		"""
		self.generateConfFile()
		self.write2Conf()




class SubjConfig():
	def __init__(self, conf, subj):
		self.conf = copy.deepcopy(conf)

		# Raise error if subjects is not in listOfSubjects
		if not subj in conf.listOfSubjects:
			raise('Internal Error, subj not defined in conf.listOfSubjects')

		confdic = self.conf.__dict__
		setattr(self, 'subjID', subj) # Set object attribute for subject ID
		for key in confdic:
			# Make sure parameter we're checking is a string
			if type(confdic[key]) == str: 
				if '%s' in confdic[key]:
					confdic[key] = confdic[key].replace('%s', subj)
				# set all other attributes from config for subjconfig, except listOfSubjects
			if key != 'listOfSubjects': setattr(self, key, confdic[key]) 


# Helper functions:

# Ensure directory exists    
def ensureDir(f):
    d = os.path.dirname(f)
    if not os.path.exists(d):
        os.makedirs(d)

# def parseTextFile(file):
# 	""""
# 	Parses a text file of parameters/variables separated by equal signs, and returns a string
# 	Intended for use of parsing *.conf files
# 	"""
# 	dic = {}
# 	with open(file) as f:
# 		for line in f:
# 			if '=' in line:
# 				# If there's an equal sign, assign it a key - val pair			
# 				(key, val) = line.split('=')
# 				key = key.strip()
# 				val = val.strip()
# 				dic[key] = val

# 	return dic








