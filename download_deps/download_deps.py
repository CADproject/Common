#the repository name and the binary name must be the same!

import argparse
import os
import shutil
import stat
import subprocess
import sys

configPath = 'external.config'
outputDirPath = '.'
msbuildPathX86 = 'C:\\Program Files (x86)\\Microsoft Visual Studio\\2017\\Community\\MSBuild\\15.0\\Bin\\MSBuild.exe'
msbuildPathX64 = 'C:\\Program Files (x86)\\Microsoft Visual Studio\\2017\\Community\\MSBuild\\15.0\\Bin\\amd64\\MSBuild.exe'
#Visual Studio 2017 Community
#$(MSBuildBinPath)	

class ScriptError(Exception):
	def __init__(self, message):
		self.message = message

class Pathes:
	def __init__(self, msbuildPathX86, msbuildPathX64, configPath, outputDirPath):
		self.msbuildPathX86 = msbuildPathX86
		self.msbuildPathX64 = msbuildPathX64
		self.configPath = configPath
		self.outputDirPath = outputDirPath

class Builder:
	def __init__(self, pathes, projects, target = 'release', platform = 'x86-64'):
		self.pathes = pathes
		self.projects = projects
		self.target = target
		self.platform = platform
		self.projectsFolder = 'projects'
		self.resultsFolder = 'bins'

	def _console(self, command):
		error = subprocess.call(command, shell=True)
		if error:
			message = 'Wrong command: {0}'.format(command)
			raise ScriptError(message)

	def _download(self, project):
		gitCloneCmd = 'git clone {0}'.format(project['repository'])
		self._console(gitCloneCmd)

		workspace = os.getcwd()
		os.chdir(project['name'])

		gitCheckoutCmd = 'git checkout {0}'.format(project['version'])
		self._console(gitCheckoutCmd)

		os.chdir(workspace)

	def _build(self, project):
		workspace = os.getcwd()
		os.chdir(project['name'])

		currentPlatform = sys.platform

		if currentPlatform == 'darwin' or currentPlatform == 'linux2':
			if self.platform == 'x86': platform = '-m32'
			elif self.platform == 'x86-64': platform = '-m64'

			cmakeCmd = 'cmake -DCMAKE_CXX_FLAGS={0} -DCMAKE_BUILD_TYPE={1} .'.format(platform,
				self.target.capitalize())
			self._console(cmakeCmd)

			makeCmd = 'make'
			self._console(makeCmd)

			if currentPlatform == 'linux2':
				projectBinary = project['name'].lower()
			else:
				projectBinary = project['name']

			shutil.move(projectBinary, os.path.join(workspace, self.resultsFolder, project['name']))

		elif currentPlatform == 'win32':
			if self.platform == 'x86':
				msbuildPath = self.pathes.msbuildPathX86
				flag = ''
			elif self.platform == 'x86-64':
				msbuildPath = self.pathes.msbuildPathX64
				flag = '-DCMAKE_GENERATOR_PLATFORM=x64'

			cmakeCmd = 'cmake {0} .'.format(flag)
			self._console(cmakeCmd)

			msbuildCmd = '"{0}" {1}.vcxproj /p:configuration={2}'.format(msbuildPath, project['name'], self.target)
			self._console(msbuildCmd)

			os.chdir(self.target.capitalize())

			application = '{0}.exe'.format(project['name'])
			library = '{0}.dll'.format(project['name'])

			if os.path.exists(application):
				result = application
			elif os.path.exists(library):
				result = library
			else:
				raise ScriptError('Build error!')

			shutil.move(result, os.path.join(workspace, self.resultsFolder, result))

		os.chdir(workspace)

	def downloadAndBuild(self):
		if not len(self.projects):
			print 'Config is empty!'
			return

		workspace = os.getcwd()

		if os.path.exists(self.projectsFolder):
			print 'WARNING: {0} already exist!'.format(self.projectsFolder)

		os.mkdir(self.projectsFolder)
		os.chdir(self.projectsFolder)
		os.mkdir(self.resultsFolder)

		for project in self.projects:
			self._download(project)
			self._build(project)

		os.chdir(workspace)

		resultsPath = os.path.join(self.projectsFolder, self.resultsFolder)

		for file in os.listdir(resultsPath):
			if os.path.isfile(os.path.join(resultsPath, file)):
				shutil.move(os.path.join(resultsPath, file), os.path.join(self.pathes.outputDirPath, file))

def getArguments():
    parser = argparse.ArgumentParser(description='''This script downloads and builds
    	projects specified in the configuration file''')

    parser.add_argument('-p', '--platform', help='platform selection', type=str, required=False,
    	choices=['x86', 'x86-64'], default='x86-64')
    parser.add_argument('-t', '--target', help='target selection', type=str, required=False,
    	choices=['release', 'debug'], default='release')
    
    return parser.parse_args()

def readConfig(configPath = '.'):
	projects = []

	file = open(configPath)

	for line in file.readlines():
		if line[0] != '#':
			projectList = line.split()
			if len(projectList):
				projectDictionary = {'name': projectList[0], 'version': projectList[1], 'repository': projectList[2]}
				projects.append(projectDictionary)

	file.close()

	return projects

def clean(folderPath):
	if not os.path.exists(folderPath):
		print 'WARNING: {0} does not exist!'.format(folderPath)
		return

	filePathes = []

	for currentDir, dirs, files in os.walk(folderPath):
		for file in files:
			filePath = os.path.join(currentDir, file)
			filePathes.append(filePath)

	for file in filePathes:
		if not os.access(file, os.W_OK):
			os.chmod(file, stat.S_IWUSR)

	shutil.rmtree(folderPath)

if __name__ == "__main__":
	args = getArguments()
	
	pathes = Pathes(msbuildPathX86, msbuildPathX64, configPath, outputDirPath)

	try:
		projects = readConfig(pathes.configPath)
	except IOError:
		print 'Wrong config file path!'
		sys.exit()

	performer = Builder(pathes, projects, args.target, args.platform)
	
	initialDirectory = os.getcwd()

	try:
		performer.downloadAndBuild()
	except ScriptError as e:
		print 'ScriptError thrown!'
		print e.message
	except Exception:
		print 'Exception thrown!'
		print sys.exc_info()
	finally:
		clean(os.path.join(initialDirectory, performer.projectsFolder))
