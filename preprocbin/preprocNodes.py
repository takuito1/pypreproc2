# Taku Ito
# Specific execute blocks, e.g., prepareMPRAGE, epiAlignment, etc.

import sys
sys.path.append('/projects/ColePreprocessingPipeline/docs/pypreproc2/preprocbin')
from run_shell_cmd import run_shell_cmd
import os
import glob
import maskbin
import re

class PrepareMPRAGE():
    """
    DESCRIPTION: Prepares and compiles anatomical MRPRAGE from raw DICOM files.  Not for HCP data use.  For use on a single subject.
    PARAMETERS: 
    	conf - a subjectConfig file
    	logname - subject's log output filename
    """

    # Nothing to init, since nextInputFilename doesn't change after this block, but still for the sake of uniformity across all nodes.
    def __init__(self, conf):
        self.conf = conf

    def run(self):    
        #make local variable
        conf = self.conf

        logname = conf.logname
        os.chdir(conf.subjfMRIDir) #change working directory to fMRI directory
            
        print 'Preparing MPRAGE file (anatomical image)'


        ##****## In the future, will want to adjust this to use os.walk to search subdirectories for files of *.dcm
        dirName = glob.glob(conf.subjRawDataDir + conf.T1_image)[0] 

        # At this point, will only search for DICOMs with *.dcm extensions, or starting with MR*
        fileFindString = 'MR*' if glob.glob(dirName + '/*.dcm') == [] else '*.dcm'
        dicomRenameDir = dirName + '/' + fileFindString

        #Sort DICOM files (to make sure they will be read in the order they were collected in) using Freesurfer
        print 'Sorting DICOM...'
        run_shell_cmd('dicom-rename ' + dicomRenameDir + ' --o ' + conf.basedir + 'SortedDICOMs/MPRAGE/MR',logname)

        #Convert DICOM files to NIFTI format using Freesurfer
        print 'Converting DICOM...'
        run_shell_cmd('mri_convert ' + conf.basedir + 'SortedDICOMs/MPRAGE/*-00001.dcm --in_type siemens --out_type nii mprage.nii.gz',logname)

        #Remove sorted DICOMs
        run_shell_cmd('rm -rf ' + conf.basedir + 'SortedDICOMs/MPRAGE',logname)

        ####
        # Skull strip MPRAGE
        # Use Freesurfer's skullstripping (very slow, but more accurate)
        if conf.runFreesurfer == True:
            run_shell_cmd('recon-all -subject ' + conf.subjID + ' -all -sd ' + conf.freesurferDir + ' -i mprage.nii.gz',logname)


        # Convert to NIFTI
        run_shell_cmd('mri_convert --in_type mgz --out_type nii ' + conf.freesurferDir + '/mri/brain.mgz mprage_skullstripped.nii',logname)


        # gzip files and removed uncompressed file
        run_shell_cmd('3dcopy mprage_skullstripped.nii mprage_skullstripped.nii.gz',logname)
        run_shell_cmd('rm mprage_skullstripped.nii',logname)

        # Compressing file
        run_shell_cmd('3dcopy mprage_skullstripped.nii.gz anat_mprage_skullstripped',logname)

        run_shell_cmd('cp ' + conf.atlasAnat + '* .',logname)




class PrepareEPI():
    """
    DESCRIPTION: Converts fMRI data to AFNI format from raw DICOMs.
    PARAMETERS: 
    	conf - a subjectConfig file
    	logname - subject's log output filename
    """
    def __init__(self, conf):
        self.conf = conf
        if self.conf.runEPIsSeparate == True:
            # This is essentially a hack to make it work for future nodes, if this Node is not run...
            self.conf.nextInputFilename.append('epi_r1')
        else:
            self.conf.nextInputFilename.append('epi')

    def run(self):
        #make local variable
        conf = self.conf

        logname = conf.logname
        os.chdir(conf.subjfMRIDir)

        numRuns = len(conf.epi_series)
        # Getting raw fMRI data folder names
        # Modify: How to identify fMRI series directory in raw data [regular expression used to get series order correct]
        ### Edit this, not very clean ###
        rawDirRunList = []
        for run in range(numRuns):
        	# find epi series
        	searchPath = glob.glob(conf.subjRawDataDir + conf.epi_series[run])[0]
        	# append to rawDirRunList
        	rawDirRunList.append(searchPath)

        print 'Raw data folder order:', rawDirRunList

        #For-loop for functions used across multiple runs (prior to run-concatenation)
        for runNum in range(1,numRuns + 1):
            print '--Run', runNum, '---'

            runRawDir = rawDirRunList[runNum-1]
            fileFindString = 'MR*' if glob.glob(runRawDir + '/*.dcm') == [] else '*.dcm'
            runRawFile = runRawDir + '/' + fileFindString
            
            # Sorting DICOM files (to make sure they will be read in the order they were collected in) using Freesurfer.
            run_shell_cmd('dicom-rename ' + runRawFile + ' --o ' + conf.basedir + '/SortedDICOMs/Run' + str(runNum) + '/MR',logname)
            
            # Converting from DICOM to NIFTI to AFNI format using Freesurfer
            run_shell_cmd('mri_convert ' + conf.basedir + '/SortedDICOMs/Run' + str(runNum) + '/*00001.dcm --in_type siemens --out_type nii epi_r' + str(runNum) + '.nii.gz',logname)
            run_shell_cmd('rm epi_r' + str(runNum) + '+orig*',logname)
            run_shell_cmd('3dcopy epi_r' + str(runNum) +'.nii.gz epi_r' + str(runNum),logname)
            run_shell_cmd('rm epi_r' + str(runNum) + '.nii.gz',logname)
            
            # Remove sorted DICOMs
            run_shell_cmd('rm -rf ' + conf.basedir + '/SortedDICOMs/Run' + str(runNum),logname)

            # If numTRsToSkip > 0, remove the first couple TRs for every epi run
            if conf.numTRsToSkip > '0':
                run_shell_cmd('3dcalc -a epi_r' + str(runNum) + '+orig"[' + conf.numTRsToSkip + '..$]" -expr ' + "'a' -prefix epi_r" + str(runNum) + ' -overwrite', logname)



    # 3rd Execute Block - Slice Time Correction
class SliceTimeCorrection():
    """
    DESCRIPTION: Performs slice time correction on fMRI data (assuming not a multiband sequence)
    PARAMETERS: 
        conf - a subjectConfig file
        logname - subject's log output filename
    """

    def __init__(self, conf):
        self.conf = conf
        self.conf.nextInputFilename.append('stc_' + conf.nextInputFilename[-1])

    def run(self):
        #make local variable
        conf = self.conf

        logname = conf.logname
        os.chdir(conf.subjfMRIDir)
        numRuns = len(conf.epi_series)

        for runNum in range(1, numRuns + 1):

            print ' - Slice Time Correction for Run', runNum, '-'
            
            run_shell_cmd('3dTshift -overwrite -Fourier -TR ' + conf.TR + ' -tpattern ' + conf.tpattern + ' -prefix ' + conf.nextInputFilename[-1] + '_r' + str(runNum) + ' ' + conf.nextInputFilename[-2] + '_r' + str(runNum) + '+orig', logname)
            
            rmFileName = glob.glob(conf.nextInputFilename[-1] + '_r' + str(runNum) + '????.????.gz')
            if rmFileName:
                run_shell_cmd('rm -v ' + rmFilename,logname)



class ConcatenateRuns():

    def __init__(self, conf):
        self.conf = conf
        self.conf.nextInputFilename.append(conf.nextInputFilename[-1] + '_allruns')
        # Update conf with new attributes/parameters

        # Construct Run List, even if this node isn't run
        runList = ' '
        concatString = '1D:'
        TRCount = 0
        numRuns = len(conf.epi_series)
        for runNum in range(1, numRuns+1):
            runList = runList + ' ' + conf.subjfMRIDir + conf.nextInputFilename[-2] + '_r' + str(runNum) + '+orig'
            concatString = concatString + ' ' + str(TRCount)
            TRCount = TRCount + conf.numTRs  ###EDIT THIS!!!

        self.conf.runList = runList
        self.conf.concatString = concatString


    def run(self):
        #make local variable
        conf = self.conf

        logname = conf.logname
        os.chdir(conf.subjfMRIDir)

        # Get concat variables from conf object
        runList = conf.runList
        concatString = conf.concatString


        numRuns = len(conf.epi_series)

        print '- Concatenating Runs -'
        print 'Run list:', runList
        print 'Concatenation string (onset times of each run):', concatString

        # Run command
        run_shell_cmd('rm -v ' + conf.nextInputFilename[-1] + '+orig*',logname)
        run_shell_cmd('3dTcat -prefix ' + conf.nextInputFilename[-1] + ' ' + runList,logname)

        # Remove intermediate analysis file to save disk space
        rm_file = glob.glob(conf.nextInputFilename[-1] + 'r_*+????.????.gz')
        if rm_file: 
            run_shell_cmd('rm -v ' + rm_file,logname)





class TalairachAlignment():

    def __init__(self, conf):
        self.conf = conf
        self.conf.nextInputFilename.append(conf.nextInputFilename[-1] + '_tlrc_al')
        

    def run(self):
        # Added if statement to see if we need to process runs separately
        if self.conf.runEPIsSeparate == True:
            for runNum in range(1,len(self.conf.epi_series)+1):
                self.conf.nextInputFilename[-1] = re.sub('epi_r[0-9]', 'epi_r' + str(runNum),self.conf.nextInputFilename[-1])
                self.conf.nextInputFilename[-2] = re.sub('epi_r[0-9]', 'epi_r' + str(runNum),self.conf.nextInputFilename[-2])
                self.runHelp()
        else:
            self.runHelp()

    def runHelp(self):    
        #make local variable
        conf = self.conf

        logname = conf.logname
        os.chdir(conf.subjfMRIDir)


        #### Talairach transform anatomical image
        print '-Run @auto_tlrc to talairach transform anatomical T1 image-'
        run_shell_cmd('@auto_tlrc -base ' + conf.atlasAnat + ' -input anat_mprage_skullstripped+orig -no_ss',logname)
        run_shell_cmd('3dcopy anat_mprage_skullstripped+tlrc anat_mprage_skullstripped_tlrc.nii.gz', logname) #format into NIFTI format

        # Create Mask
        run_shell_cmd("3dcalc -overwrite -a anat_mprage_skullstripped+tlrc -expr 'ispositive(a)' -prefix " + conf.subjMaskDir + "/wholebrain_mask.nii.gz" ,logname)
        # Link anatomical image to mask directory for checking alignment
        run_shell_cmd('ln -s anat_mprage_skullstripped_tlrc.nii.gz ' + conf.subjMaskDir,logname)


        print '-Run align_epi_anat.py to align EPIs to MPRAGE, motion correct, and Talairach transform EPIs (output in 222 space)-'

        print 'Make sure Python is version 2.6 or greater (ColeLabMac should be version 2.7)'
        run_shell_cmd('python -V',logname)

        # Correcting for motion, aligning fMRI data to MPRAGE, and aligning fMRI data to Talairach template [applying all transformation at once reduces reslicing artifacts]
        # [You could alternatively analyze all of the data, then Talairach transform the statistics (though this would make extraction of time series based on Talairached ROIs difficult)]
        # Visit for more info: http://afni.nimh.nih.gov/pub/dist/doc/program_help/align_epi_anat.py.html

        run_shell_cmd('align_epi_anat.py -overwrite -anat anat_mprage_skullstripped+orig -epi ' + conf.nextInputFilename[-2] + '+orig -epi_base 10 -epi2anat -anat_has_skull no -AddEdge -epi_strip 3dSkullStrip -ex_mode quiet -volreg on -deoblique on -tshift off -tlrc_apar anat_mprage_skullstripped+tlrc -master_tlrc ' +  conf.atlasEPI,logname)

        # Convert to NIFTI
        run_shell_cmd('3dcopy ' + conf.nextInputFilename[-1] + '+tlrc ' + conf.nextInputFilename[-1] + '.nii.gz',logname)
        run_shell_cmd('cp ' + conf.nextInputFilename[-2] + "_vr_motion.1D allruns_motion_params.1D",logname)





class CheckMotionParams():

    def __init__(self, conf, showPlot=True):
        self.conf = conf
        self.showPlot = showPlot

    def run(self):
        # Added if statement to see if we need to process runs separately
        if self.conf.runEPIsSeparate == True:
            for runNum in range(1,len(self.conf.epi_series)+1):
                self.conf.nextInputFilename[-1] = re.sub('epi_r[0-9]', 'epi_r' + str(runNum),self.conf.nextInputFilename[-1])
                self.conf.nextInputFilename[-2] = re.sub('epi_r[0-9]', 'epi_r' + str(runNum),self.conf.nextInputFilename[-2])
                self.runHelp()
        else:
            self.runHelp()
        
    def runHelp(self):
        #make local variable
        conf = self.conf

        logname = conf.logname
        os.chdir(conf.subjfMRIDir)

        # Plotting motion parameters
        if self.showPlot == True:
            run_shell_cmd('1dplot -sep_scl -plabel ' + str(conf.subjID) + "Motion -volreg allruns_motion_params.1D'[0..5]'",logname)

        run_shell_cmd('echo "Mean, standard deviation, and absolute deviation of subject\'s motion in mm (left to right), by x,y,z direction (top to bottom):" > MotionInfo.txt',logname)
        run_shell_cmd("3dTstat -mean -stdev -absmax -prefix stdout: allruns_motion_params.1D'[0..2]'\\'" + " >> MotionInfo.txt",logname)
        run_shell_cmd('cat MotionInfo.txt',logname)





class TimeSeriesExtraction():

    def __init__(self, conf):
        self.conf = conf

    def run(self):
        # Added if statement to see if we need to process runs separately
        if self.conf.runEPIsSeparate == True:
            for runNum in range(1,len(self.conf.epi_series)+1):
                # Update epi run name so we can analyze EPI scans separately for both input and output filenames
                self.conf.nextInputFilename[-1] = re.sub('epi_r[0-9]', 'epi_r' + str(runNum),self.conf.nextInputFilename[-1])
                self.conf.nextInputFilename[-2] = re.sub('epi_r[0-9]', 'epi_r' + str(runNum),self.conf.nextInputFilename[-2])
                # Create separate time series 1D files for each scan, since we're analyzing each run separately.
                self.conf.wm_timeseries = self.conf.subjID + '_WM_timeseries_r' + str(runNum) 
                self.conf.ventricles_timeseries = self.conf.subjID + '_ventricles_timeseries_r' + str(runNum) 
                self.conf.wholebrain_timeseries = self.conf.subjID + '_wholebrainsignal_timeseries_r' + str(runNum) 
                # run
                self.runHelp()
        else:
            # Instantiate appropriate timeseries output names.  If runs are concatenated, only need one timeseries files.
            self.conf.wm_timeseries = self.conf.subjID + '_WM_timeseries'
            self.conf.ventricles_timeseries = self.conf.subjID + '_ventricles_timeseries'
            self.conf.wholebrain_timeseries = self.conf.subjID + '_wholebrainsignal_timeseries'
            # run
            self.runHelp()


    def runHelp(self):
        #make local variable
        conf = self.conf

        logname = conf.logname
        os.chdir(conf.subjfMRIDir)

        print '--Extract time series from white matter, ventricle masks--'
        run_shell_cmd('3dmaskave -quiet -mask ' + conf.subjMaskDir + conf.subjID + '_wmMask_func_eroded.nii.gz ' + conf.nextInputFilename[-1] + '.nii.gz > ' + conf.wm_timeseries + '.1D',logname)
        run_shell_cmd('3dmaskave -quiet -mask ' + conf.subjMaskDir + conf.subjID + '_ventricles_func_eroded.nii.gz ' + conf.nextInputFilename[-1] + '.nii.gz > ' + conf.ventricles_timeseries + '.1D',logname)


        print '--Extract whole brain signal--'        
        os.chdir(conf.subjMaskDir)

        if conf.hcpData == False: # no need to run @auto_tlrc on hcpdata
            # Transform aseg to TLRC space
            run_shell_cmd('@auto_tlrc -apar ' + conf.subjfMRIDir + 'anat_mprage_skullstripped+tlrc -input ' + conf.subjID + '_fs_seg.nii.gz',logname)

        run_shell_cmd("3dcalc -overwrite -a " + conf.subjID + "_fs_seg.nii.gz -expr 'ispositive(a)' -prefix " + conf.subjID + '_wholebrainmask.nii.gz',logname)

        # Resample to functional space
        run_shell_cmd('3dresample -overwrite -master ' + conf.subjfMRIDir + conf.nextInputFilename[-1] + '.nii.gz -inset ' + conf.subjID + '_wholebrainmask.nii.gz -prefix ' + conf.subjID + '_wholebrainmask_func.nii.gz',logname)

        # Dilate mask by 1 functional voxel (just in case the resampled anatomical mask is off by a bit)
        run_shell_cmd("3dLocalstat -overwrite -nbhd 'SPHERE(-1)' -stat 'max' -prefix " + conf.subjID + '_wholebrainmask_func_dil1vox.nii.gz ' + conf.subjID + '_wholebrainmask_func.nii.gz',logname)

        os.chdir(conf.subjfMRIDir)
        run_shell_cmd('3dmaskave -quiet -mask ' + conf.subjMaskDir + conf.subjID + '_wholebrainmask_func_dil1vox.nii.gz ' + conf.nextInputFilename[-1] + '.nii.gz > ' + conf.wholebrain_timeseries + '.1D',logname)



class RunGLM():

    def __init__(self, conf):
        self.conf = conf
        if conf.GLM['type'] == 'rsfcMRI':
            self.conf.nextInputFilename.append('NuissanceResid_' + self.conf.nextInputFilename[-1])
        elif conf.GLM['type'] == 'Activation':
            self.conf.nextInputFilename.append(conf.AnalysisName + '_outbucket')
        else:
            raise Exception("Not a valid type of GLM. Please edit GLM 'type' input to either 'Activation' or 'rsfcMRI'")

        # make sure concatString is defined as empty, for EPIs
        if conf.runEPIsSeparate == True:
            self.conf.concatString = ''

    def run(self):
        # Added if statement to see if we need to process runs separately
        if self.conf.runEPIsSeparate == True:
            for runNum in range(1,len(self.conf.epi_series)+1):
                # Update epi run name so we can analyze EPI scans 
                self.conf.nextInputFilename[-1] = re.sub('epi_r[0-9]', 'epi_r' + str(runNum),self.conf.nextInputFilename[-1])
                self.conf.nextInputFilename[-2] = re.sub('epi_r[0-9]', 'epi_r' + str(runNum),self.conf.nextInputFilename[-2])
                # Create separate time series 1D files for each scan, since we're analyzing each run separately.
                # In the future, another alternative and cleaner way to deal with this is to not have to re-instantiate this in the conf file, and rather, just keep each run's version in a list so the code in preprocNodes can be re-used.
                self.conf.wm_timeseries = self.conf.subjID + '_WM_timeseries_r' + str(runNum)
                self.conf.ventricles_timeseries = self.conf.subjID + '_ventricles_timeseries_r' + str(runNum)
                self.conf.wholebrain_timeseries = self.conf.subjID + '_wholebrainsignal_timeseries_r' + str(runNum)
                # run
                self.runHelp()
        else:
            # Instantiate appropriate timeseries output names.  If runs are concatenated, only need one timeseries files.
            self.conf.wm_timeseries = self.conf.subjID + '_WM_timeseries'
            self.conf.ventricles_timeseries = self.conf.subjID + '_ventricles_timeseries'
            self.conf.wholebrain_timeseries = self.conf.subjID + '_wholebrainsignal_timeseries'
            # run
            self.runHelp()

    def organizeStimTimes(self):
        # Make local variables for better readability
        conf = self.conf
        GLM = self.conf.GLM
        motionregs = GLM['motionregressors']
        stimfiles = GLM['stimtimes']

        stimtimes = []
        if GLM['type'] == 'Activation':
            # compute number of motion regressors
            num_motionregs = len(GLM['motionregressors'])
            # compute number of stimulus times
            num_stims = len(GLM['stimtimes'])/2 #needs to be divided by 2, since also has a label associated with it

            # compute numstimes total
            totalnumstimes = num_motionregs + num_stims

            # Keep track of stimcount
            stimcount = 1

            # first evaluate motion regressors
            for key in motionregs:
                stimtimes.append('-stim_file ' + str(stimcount) + ' ' + conf.subjfMRIDir + motionregs[key] + ' -stim_base ' + str(stimcount) + ' ')
                stimcount += 1

            # next evaluate stimulus task times
            for key in stimfiles:
                # Replace %s glob with proper subject ID
                stimfiles[key][0] = stimfiles[key][0].replace('%s', conf.subjID)

                # Now append correct stimulus file to array
                stimtimes.append('-stim_times ' + str(stimcount) + ' ' + conf.stimFileDir + stimfiles[key][0] + ' -stim_label ' + str(stimcount) + ' ' + stimfiles[key][1] + ' ')
                stimcount += 1

            # Return stimtimes array
            return stimtimes

        elif GLM['type'] == 'rsfcMRI':
            # First make sure to include wm, ventricle and whole brain timeseries regressors (and derivatives) manually
            stimtimes.append('-stim_file 1 ' + conf.wm_timeseries + '.1D -stim_label 1 WM ')
            stimtimes.append('-stim_file 2 ' + conf.ventricles_timeseries + '.1D -stim_label 2 Vent ')
            stimtimes.append('-stim_file 3 ' + conf.wm_timeseries + '_deriv.1D -stim_label 3 WMDeriv ')
            stimtimes.append('-stim_file 4 ' + conf.ventricles_timeseries + '_deriv.1D -stim_label 4 VentDeriv ')
            if 'GSR' in GLM.keys():
                if GLM['GSR'] == True:
                    print '***Including GSR in GLM***'
                    stimtimes.append("-stim_file 5 " + conf.wholebrain_timeseries + '.1D -stim_label 5 WholeBrain ')
                    stimtimes.append("-stim_file 6 " + conf.wholebrain_timeseries + '_deriv.1D -stim_label 6 WholeBrainDeriv ')
                    stimcount = 7 # need to start at 7 since we already included the first 6 stimtimes

                else:
                    print '***Not including GSR in GLM***'
                    stimcount = 5 # need to start at 5 since we already included the first 4 stimtimes

            for key in motionregs:
                stimtimes.append("-stim_file " + str(stimcount) + ' ' + conf.subjfMRIDir + motionregs[key] + " -stim_base " + str(stimcount) + ' ')
                stimcount += 1

            # return stimtimes array
            return stimtimes


        else: 
            raise Exception("Not a valid type of GLM. Please edit GLM 'type' input to either 'Activation' or 'rsfcMRI'")

    def runHelp(self):    

        #make local variable
        conf = self.conf
        GLM = self.conf.GLM

        logname = conf.logname
        os.chdir(conf.subjfMRIDir)

        run_shell_cmd('cp Movement_Regressors_Rest_allruns.1D allruns_motion_params.1D', logname)

        run_shell_cmd('1d_tool.py -overwrite -infile ' + conf.wm_timeseries + '.1D -derivative -write ' + conf.wm_timeseries + '_deriv.1D', logname)
        run_shell_cmd('1d_tool.py -overwrite -infile ' + conf.ventricles_timeseries + '.1D -derivative -write ' + conf.ventricles_timeseries + '_deriv.1D', logname)
        run_shell_cmd('1d_tool.py -overwrite -infile ' + conf.wholebrain_timeseries + '.1D -derivative -write ' + conf.wholebrain_timeseries + '_deriv.1D', logname)

        print 'Run GLM to remove nuisance time series (motion, white matter, ventricles)'
        input = '-input ' + conf.nextInputFilename[-2] + '.nii.gz ' if GLM['input'] == None else GLM['input']
        mask = '-mask ' + conf.subjMaskDir + conf.subjID + '_gmMask_func_dil1vox.nii.gz '
        concat = '' if GLM['concat'] == False else '-concat ' + '"' + conf.concatString + '" '
        polort = '-polort ' + str(GLM['polort']) + ' '
        stimtimes = self.organizeStimTimes()
        num_stimts = '-num_stimts ' + str(len(stimtimes)) + ' '
        # make stimtimes into a single string
        stimtimes = ''.join(stimtimes)
        # stimfile1 = '-stim_file 1 ' + conf.wm_timeseries + '.1D -stim_label 1 WM '
        # stimfile2 = '-stim_file 2 ' + conf.ventricles_timeseries + '.1D -stim_label 2 Vent '
        # stimfile3 = '-stim_file 3 ' + conf.wm_timeseries + '_deriv.1D -stim_label 3 WMDeriv '
        # stimfile4 = '-stim_file 4 ' + conf.ventricles_timeseries + '_deriv.1D -stim_label 4 VentDeriv '
        # stimfile5 = "-stim_file 5 allruns_motion_params.1D'[0]' -stim_base 5 "
        # stimfile6 = "-stim_file 6 allruns_motion_params.1D'[1]' -stim_base 6 "
        # stimfile7 = "-stim_file 7 allruns_motion_params.1D'[2]' -stim_base 7 "
        # stimfile8 = "-stim_file 8 allruns_motion_params.1D'[3]' -stim_base 8 "
        # stimfile9 = "-stim_file 9 allruns_motion_params.1D'[4]' -stim_base 9 "
        # stimfile10 = "-stim_file 10 allruns_motion_params.1D'[5]' -stim_base 10 "
        # these stimfiles are commented out because this had to be adapted from analyzing the HCP rest data
        # stimfile11 = "-stim_file 11 rest_allruns_motion_params.1D'[6]' -stim_base 11 "
        # stimfile12 = "-stim_file 12 rest_allruns_motion_params.1D'[7]' -stim_base 12 "
        # stimfile13 = "-stim_file 13 rest_allruns_motion_params.1D'[8]' -stim_base 13 "
        # stimfile14 = "-stim_file 14 rest_allruns_motion_params.1D'[9]' -stim_base 14 "
        # stimfile15 = "-stim_file 15 rest_allruns_motion_params.1D'[10]' -stim_base 15 "
        # stimfile16 = "-stim_file 16 rest_allruns_motion_params.1D'[11]' -stim_base 16 "
        # stimfile11 = "-stim_file 11 " + conf.wholebrain_timeseries + '.1D -stim_label 11 WholeBrain '
        # stimfile12 = "-stim_file 12 " + conf.wholebrain_timeseries + '_deriv.1D -stim_label 12 WholeBrainDeriv '
        xsave = '-xsave -x1D xmat_rall.x1D -xjpeg xmat_rall.jpg '
        
        gltsym = '' if GLM['gltsym'] == None else GLM['gltsym'] + ' '
        errts = '' if GLM['errts'] == None else '-errts ' + GLM['errts'] + ' '
        fdr = '' if  GLM['noFDR'] == False else '-noFDR '
        fout = '-fout ' if GLM['fout'] == True else ''
        tout = '-tout ' if GLM['tout'] == True else ''
        if 'jobs' in GLM.keys():
            jobs = '-jobs ' + str(GLM['jobs']) + ' -float '
        else:
            jobs = '-jobs 1 -float '

        # change outbucket output name according to type of GLM run
        if GLM['type'] == 'Activation':
            bucket = '-bucket ' + conf.AnalysisName + '_outbucket -cbucket ' + conf.AnalysisName + '_cbucket'
        else:
            bucket = '-bucket NuissanceResid_outbucket_' + conf.nextInputFilename[-2] + '+tlrc -overwrite' 


        glm_command = '3dDeconvolve ' + input + mask + concat + polort + num_stimts + stimtimes + gltsym + fout + tout + xsave + errts + jobs + fdr + bucket

        print 'Running the GLM command:', glm_command
        run_shell_cmd(glm_command, logname)

        if GLM['type'] == 'rsfcMRI':
            run_shell_cmd('rm ' + conf.nextInputFilename[-1] + '*', logname)
            run_shell_cmd('3dcopy NuissanceResid_Resids+tlrc ' + conf.nextInputFilename[-1] + '+tlrc', logname)
            run_shell_cmd('rm NuissanceResid_Resids+tlrc', logname)
        elif GLM['type'] == 'Activation':
            run_shell_cmd('1dplot -sep_scl -plabel ' + conf.subjID + 'DesignMatrix xmat_rall.x1D &', logname)


class SpatialSmoothing():

    def __init__(self, conf):
        self.conf = conf
        self.conf.nextInputFilename.append('smInMask_' + conf.nextInputFilename[-1])


    def run(self):
        if self.conf.runEPIsSeparate == True:
            print 'Running separately for each EPI scan...'
            for runNum in range(1,len(self.conf.epi_series)+1):
                self.conf.nextInputFilename[-1] = re.sub('epi_r[0-9]', 'epi_r' + str(runNum),self.conf.nextInputFilename[-1])
                self.conf.nextInputFilename[-2] = re.sub('epi_r[0-9]', 'epi_r' + str(runNum),self.conf.nextInputFilename[-2])
                self.runHelp()
        else:
            print 'Running on concatenated EPIs...'
            self.runHelp()


    def runHelp(self):
        #make local variable
        conf = self.conf

        logname = conf.logname
        os.chdir(conf.subjfMRIDir)

        print '-Spatially smooth data-'

        run_shell_cmd('3dBlurInMask -input ' + conf.nextInputFilename[-2] + '+tlrc -FWHM ' + str(conf.FWHMSmoothing) + ' -mask ' + conf.subjMaskDir + conf.subjID + '_gmMask_func_dil1vox.nii.gz -prefix ' + conf.nextInputFilename[-1] + '.nii.gz', logname)



class PercentSignalNormalization():
    """
    Updated: 10/14/14
    Reason: To deal with inhomogeneities in RUBIC's multiband EPI data
    """

    def __init__(self, conf):
        self.conf = conf
        self.conf.nextInputFilename.append(conf.nextInputFilename[-1] + '_pscNorm')

    def run(self):
        if self.conf.runEPIsSeparate == True:
            print 'Running separately for each EPI scan...'
            for runNum in range(1,len(self.conf.epi_series)+1):
                self.conf.nextInputFilename[-1] = re.sub('epi_r[0-9]', 'epi_r' + str(runNum),self.conf.nextInputFilename[-1])
                self.conf.nextInputFilename[-2] = re.sub('epi_r[0-9]', 'epi_r' + str(runNum),self.conf.nextInputFilename[-2])
                self.runHelp()
        else:
            print 'Running on concatenated EPIs...'
            self.runHelp()


    def runHelp(self):
        # make local variable
        conf = self.conf
        logname = conf.logname

        print '-Percent Signal Change Normalization-'

        os.chdir(conf.subjfMRIDir)
        print '-Deoblique whole brain mask to align with original EPI image-'
        run_shell_cmd('3dWarp -card2oblique ' + conf.nextInputFilename[-2] + '+orig -prefix tmp_deoblique_wbm.nii.gz ' + conf.subjMaskDir + conf.subjID + '_wholebrainmask.nii.gz', logname)
        run_shell_cmd('3dresample -overwrite -master ' + conf.subjfMRIDir + conf.nextInputFilename[-2] + '+orig -inset tmp_deoblique_wbm.nii.gz -prefix tmp_deoblique_wbm_func.nii.gz',logname)
        print '-Run 3dTstat to get the mean activation for each voxel across time-'
        run_shell_cmd('3dTstat -mean -prefix tmp_tmean.nii.gz ' + conf.nextInputFilename[-2] + '+orig', logname)
        print '-Now run percent signal change, masking to deobliqued, whole brain mask-'
        run_shell_cmd('3dcalc -a ' + conf.nextInputFilename[-2] + "+orig -b tmp_tmean.nii.gz -c tmp_deoblique_wbm_func.nii.gz -expr '100 * a/b * ispositive(c)' -prefix " + conf.nextInputFilename[-1], logname)
        print '-Deleting intermediate files...-'
#        run_shell_cmd('rm -v tmp_deoblique_wbm.nii.gz tmp_tmean.nii.gz tmp_deoblique_wbm_func.nii.gz',logname)



class CustomCmd():
    """
    DESCRIPTION: This is an object that wraps a custom command.
    """

    def __init__(self,cmd,sconf):
        self.dict = cmd
        self.conf = sconf
        for key in self.dict:
            # Make sure self.dict[key] is a string, since we'll be replacing those strings with key words (with '%' signs in front)
            if isinstance(self.dict[key], str):
                # Currently only searching and replacing the below parameters
                self.dict[key] = self.dict[key].replace('%nextInputFilename',sconf.nextInputFilename[-1])
                self.dict[key] = self.dict[key].replace('%s', sconf.subjID)
                self.dict[key] = self.dict[key].replace('%input', self.dict['input'])
                self.dict[key] = self.dict[key].replace('%output', self.dict['output'])
        self.input = self.dict['input']
        self.output = self.dict['output']
        self.cmd = self.dict['cmd']
        self.nextInput = self.dict['insertOutputAsNextInput']
        
        if self.nextInput == True:
            self.conf.nextInputFilename.append(self.output)

    def run(self):
        run_shell_cmd(self.cmd, self.conf.logname)



    

