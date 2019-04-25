import pubrunner
import tempfile
import shutil
import os
import hashlib

def calcSHA256(filename):
	return hashlib.sha256(open(filename, 'rb').read()).hexdigest()

class TempDir:
	def __init__(self):
		pass

	def __enter__(self):
		self.tempDir = tempfile.mkdtemp()
		return self.tempDir

	def __exit__(self, type, value, traceback):
		shutil.rmtree(self.tempDir)

def test_download_http():
	with TempDir() as allResourcesDirectory, TempDir() as workingDirectory:
		resource = pubrunner.Resource(allResourcesDirectory,workingDirectory,'test','http://neverssl.com/index.html')
		resource.download()

		directory = resource.downloadDirectory

		expectedFileHashes = {'index.html':'dee5056021025e6fcd5d06183c4f72b289caa88e05ffdeb364a05ab2d28fd10f'}
		fileHashes = { f:calcSHA256(os.path.join(directory,f)) for f in os.listdir(directory) }
		assert expectedFileHashes == fileHashes

def test_download_https():
	with TempDir() as allResourcesDirectory, TempDir() as workingDirectory:
		resource = pubrunner.Resource(allResourcesDirectory,workingDirectory,'test','https://raw.githubusercontent.com/Linuxbrew/brew/master/README.md')
		resource.download()

		directory = resource.downloadDirectory

		expectedFileHashes = {'README.md':'8267267c8f7a2abefbfe37c81f75dbfa68682d200d2cb547a3c0bf1a4a7f7fd8'}
		fileHashes = { f:calcSHA256(os.path.join(directory,f)) for f in os.listdir(directory) }
		assert expectedFileHashes == fileHashes

def test_download_ftp():
	with TempDir() as allResourcesDirectory, TempDir() as workingDirectory:
		resource = pubrunner.Resource(allResourcesDirectory,workingDirectory,'test','ftp://ftp.ncbi.nlm.nih.gov/robots.txt')
		resource.download()

		directory = resource.downloadDirectory

		expectedFileHashes = {'robots.txt':'331ea9090db0c9f6f597bd9840fd5b171830f6e0b3ba1cb24dfa91f0c95aedc1'}
		fileHashes = { f:calcSHA256(os.path.join(directory,f)) for f in os.listdir(directory) }
		assert expectedFileHashes == fileHashes

def test_download_zenodo():
	with TempDir() as allResourcesDirectory, TempDir() as workingDirectory:
		resource = pubrunner.Resource(allResourcesDirectory,workingDirectory,'test','https://zenodo.org/record/2643199')
		resource.download()

		directory = resource.downloadDirectory

		expectedFileHashes = {'TheOpenAIREResearchGraphDataModel_v_1_3.pdf':'ed5a789f07091f86e8816d244a7593fa3aee4be67e585c0875983a4333527e71'}
		fileHashes = { f:calcSHA256(os.path.join(directory,f)) for f in os.listdir(directory) }
		assert expectedFileHashes == fileHashes

def te_resourceByName():
	resource = pubrunner.Resource.byName('PUBMED')

def te_convert():
	resource = pubrunner.Resource(sourceName='PUBMED_README',requiredFormat='biocxml')
	resource.download()
	resource.convert()

	directory = resource.getDirectory()

	expectedMD5s = {}
	for f in os.listdir(directory):
		md5sum = calcMD5(os.path.join(directory,f))
		assert f in expectedMD5s
		assert md5sum == expectedMD5s[f]
	
