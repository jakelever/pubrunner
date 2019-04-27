import pubrunner
import tempfile
import shutil
import os
import hashlib
import pytest

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
		
def test_download_urls():
	with TempDir() as allResourcesDirectory, TempDir() as workingDirectory:
		resource = pubrunner.Resource(allResourcesDirectory,workingDirectory,'test',['https://raw.githubusercontent.com/Linuxbrew/brew/master/README.md','http://neverssl.com/index.html'])
		resource.download()

		directory = resource.downloadDirectory

		expectedFileHashes = {'README.md':'8267267c8f7a2abefbfe37c81f75dbfa68682d200d2cb547a3c0bf1a4a7f7fd8','index.html':'dee5056021025e6fcd5d06183c4f72b289caa88e05ffdeb364a05ab2d28fd10f'}
		fileHashes = { f:calcSHA256(os.path.join(directory,f)) for f in os.listdir(directory) }
		assert expectedFileHashes == fileHashes

@pytest.mark.skipif(os.environ.get('TRAVIS', 'False') == 'True', reason="Travis-CI doesn't support FTP")
def test_download_ftp():
	with TempDir() as allResourcesDirectory, TempDir() as workingDirectory:
		resource = pubrunner.Resource(allResourcesDirectory,workingDirectory,'test','ftp://ftp.cs.brown.edu/pub/README')
		resource.download()

		directory = resource.downloadDirectory

		expectedFileHashes = {'README':'b409ee099964d02ae160358077c87f74687565eb313bbf6dd98fee1062f97474'}
		fileHashes = { f:calcSHA256(os.path.join(directory,f)) for f in os.listdir(directory) }
		assert expectedFileHashes == fileHashes

@pytest.mark.skipif(os.environ.get('TRAVIS', 'False') == 'True', reason="Travis-CI doesn't support FTP")
def test_download_ftp_dir():
	with TempDir() as allResourcesDirectory, TempDir() as workingDirectory:
		resource = pubrunner.Resource(allResourcesDirectory,workingDirectory,'test','ftp://ftp.cs.brown.edu/pub/arpa/')
		resource.download()

		directory = resource.downloadDirectory

		expectedFileHashes = {'A8225_pic.gif': '164b32e4023d1449305c4b3ed54af8ed578cc0e6fa471a8313a266f64e55abb8', 'A8225_sched.gif': '61214169047dce8d9a49c87f45e3ccfdab012d269a9c88c266f9878339ca9ac1'}
		fileHashes = { f:calcSHA256(os.path.join(directory,f)) for f in os.listdir(directory) }
		print(fileHashes)
		assert expectedFileHashes == fileHashes

def test_download_zenodo():
	with TempDir() as allResourcesDirectory, TempDir() as workingDirectory:
		resource = pubrunner.Resource(allResourcesDirectory,workingDirectory,'test','https://zenodo.org/record/2643199')
		resource.download()

		directory = resource.downloadDirectory

		expectedFileHashes = {'TheOpenAIREResearchGraphDataModel_v_1_3.pdf':'ed5a789f07091f86e8816d244a7593fa3aee4be67e585c0875983a4333527e71'}
		fileHashes = { f:calcSHA256(os.path.join(directory,f)) for f in os.listdir(directory) }
		assert expectedFileHashes == fileHashes

def test_download_pubmed_single():
	with TempDir() as allResourcesDirectory, TempDir() as workingDirectory:
		resource = pubrunner.Resource(allResourcesDirectory,workingDirectory,'test','https://www.ncbi.nlm.nih.gov/pubmed/27251290',email='jlever@bcgsc.ca')
		resource.download()

		directory = resource.downloadDirectory

		expectedFileHashes = {'pubmed_27251290.xml': 'fccbe19b697c9bde4456ff13da9d209468d5125cdef09066f9cb7ff429c892e8'}
		fileHashes = { f:calcSHA256(os.path.join(directory,f)) for f in os.listdir(directory) }
		assert expectedFileHashes == fileHashes

def test_download_pmc_single():
	with TempDir() as allResourcesDirectory, TempDir() as workingDirectory:
		resource = pubrunner.Resource(allResourcesDirectory,workingDirectory,'test','https://www.ncbi.nlm.nih.gov/pmc/4067548',email='jlever@bcgsc.ca')
		resource.download()

		directory = resource.downloadDirectory

		expectedFileHashes = {'pmc_4067548.nxml': '2fcca2820988f38a3da91f32c93973dd4aad0da447b9e31cd90b8758f9204442'}
		fileHashes = { f:calcSHA256(os.path.join(directory,f)) for f in os.listdir(directory) }
		assert expectedFileHashes == fileHashes

def test_download_github():
	with TempDir() as allResourcesDirectory, TempDir() as workingDirectory:
		resource = pubrunner.Resource(allResourcesDirectory,workingDirectory,'test','https://github.com/jakelever/tree2maze')
		resource.download()

		directory = resource.downloadDirectory

		expectedFileHashes = {'README.md': '114643d3eeef9ac93d1d6409a17edf58d95ededdd22324663db8a7939a2ef9bd', '.gitignore': '63e7ffd5caa49c46ef4c9cf01640102328e6b176d07b33ec2315c93a983c6b84', 'tree2maze.py': '6e47862ef148e650301c15d06e5c7babe3b73c6f5dbd1200185a59bfce6d62e6', 'example_with_text.png': '69e4088a2e30e5951c4010231ea5a86ca5617e1d025aa0cd4c7d37150cf66d72', 'example_tree.tsv': '8b7bf40122c65b069d90b90d221ae5cca12d175a86ddd37cfc21f98c7372755e'}
		fileHashes = { f:calcSHA256(os.path.join(directory,f)) for f in os.listdir(directory) if os.path.isfile(os.path.join(directory,f)) }
		assert expectedFileHashes == fileHashes

def test_update_http():
	with TempDir() as allResourcesDirectory, TempDir() as workingDirectory:
		directory = os.path.join(allResourcesDirectory,'test')
		os.makedirs(directory)
		with open(os.path.join(directory,'index.html'),'w') as f:
			f.write("\n".join(map(str,range(1000))))
		
		expectedFileHashes = {'index.html':'cdcaf63295eb44b199f8945bea9040fc067d26c0af90e23fefc77367534bc75e'}
		fileHashes = { f:calcSHA256(os.path.join(directory,f)) for f in os.listdir(directory) }
		assert expectedFileHashes == fileHashes

		resource = pubrunner.Resource(allResourcesDirectory,workingDirectory,'test','http://neverssl.com/index.html')
		resource.download()

		assert directory == resource.downloadDirectory

		expectedFileHashes = {'index.html':'dee5056021025e6fcd5d06183c4f72b289caa88e05ffdeb364a05ab2d28fd10f'}
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
	
