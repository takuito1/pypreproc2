#!/usr/bin/env python

# Taku Ito
# 07/03/2014

# PyPreproc Modular Version 1.0
# Implements a more modular approach in hopes of simplifying and re-using code, and also to make certain pipelines more configurable based on the type of data.
# Requires to use of a config file, (*.conf) to set all pipeline parameters.

import sys
sys.path.append('preprocbin')
from workflows import *
from run_shell_cmd import run_shell_cmd
import os
import glob
import maskbin
import config
import utils
import executeBlocks as block
from multiprocessing import Pool

configfile = '/projects/IndivRITL/docs/scripts/pypreproc/pilotPreproc.yaml'

configfile = raw_input('Give the full path of your configuration file (with a .yaml extension): ')

# Creates new conf file
conf = config.Config(configfile)

# Creating a list of subject config files (an iterable to be input)
sconf = [] 
subjCount = 0
for subj in conf.listOfSubjects:
	sconf.append(config.SubjConfig(conf,subj))
	utils.ensureSubjDirsExist(sconf[subjCount])
	utils.createLogFile(sconf[subjCount])
	subjCount += 1

def pipeline(sconf):
	sconf = block.prepareMPRAGE(sconf)
	sconf = block.prepareEPI(sconf)
	# sconf = block.concatenateRuns(sconf, sconf.logname)
	sconf.nextInputFilename[-1] = 'epi_r1'
	sconf = block.talairachAlignment(sconf)
	sconf = block.checkMotionParams(sconf)
	sconf = maskbin.create_gmMask(sconf)
	sconf = maskbin.create_wmMask(sconf)
	sconf = maskbin.createVentricleMask(sconf)
	sconf = block.timeSeriesExtraction(sconf)
	sconf = block.runGLM(sconf)
	sconf = block.spatialSmoothing(sconf)

def runParallel(conf, sconf):
	pool = Pool(processes=conf.nproc)
	pool.map_async(pipeline, sconf).get(9999999)


runParallel(conf,sconf)






