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
		
def test_download_urls():
	with TempDir() as allResourcesDirectory, TempDir() as workingDirectory:
		resource = pubrunner.Resource(allResourcesDirectory,workingDirectory,'test',['https://raw.githubusercontent.com/Linuxbrew/brew/master/README.md','http://neverssl.com/index.html'])
		resource.download()

		directory = resource.downloadDirectory

		expectedFileHashes = {'README.md':'8267267c8f7a2abefbfe37c81f75dbfa68682d200d2cb547a3c0bf1a4a7f7fd8','index.html':'dee5056021025e6fcd5d06183c4f72b289caa88e05ffdeb364a05ab2d28fd10f'}
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

def test_download_ftp_dir():
	with TempDir() as allResourcesDirectory, TempDir() as workingDirectory:
		resource = pubrunner.Resource(allResourcesDirectory,workingDirectory,'test','ftp://ftp.ncbi.nlm.nih.gov/pub/GeneTests/')
		resource.download()

		directory = resource.downloadDirectory

		expectedFileHashes = {'README.html': '8063908d0dd4ae7274cd0df055c6b19f37f33e343969e4aed613ace9f6854fd8', 'disease_OMIM.txt': 'f090e0530f126171fe5c8df4265a1907c07c58abb99ee910820c26571e1775e0', 'disease_OMIM_Gene_NonUS.txt': '9a2d74df33015fd47031af90f708de90f0dce4d7fbe7deaf0fe02f4156eb5b47', 'disease_OMIM_Gene_US.txt': '85be0b7b983ba2ce2871c886bd4686ab2add5b2d6eca4d0abb320bd593ba75dd', 'disease_hierarchy.txt': '5b979a2c409049d3e1b13840addb3b69eed9ad996c1bb0978f1cabaddf47cc81', 'data_to_build_custom_reports.txt': '7fbc28bbd1eec9a154af30f4bef2dda46dea0a6ea1228e7e66391e91ad2f8ceb'}
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
	
