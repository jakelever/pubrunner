
import os

import pubrunner.download

def eutilsToFile(settings,db,id,filename):
	if not 'email' in settings:
		raise RuntimeError("You must provide an email in the global or local settings file")
	Entrez.email = settings['email']
	handle = Entrez.efetch(db=db, id=id, rettype="gb", retmode="xml")
	with codecs.open(filename,'w','utf-8') as f:
		xml = handle.read()
		f.write(xml)

class Resource:
	def __init__(self,allResourcesDirectory,workingDirectory,name,urls):#,name,sourceFormat,projectFormat,removePMCOADuplicates,usePubmedHashes,pmids,pmcids):
		assert isinstance(allResourcesDirectory, str)
		assert isinstance(workingDirectory, str)
		assert os.path.isdir(allResourcesDirectory)
		assert os.path.isdir(workingDirectory)

		assert isinstance(name, str)
		assert isinstance(urls, str) or isinstance(urls, list)
		if isinstance(urls,list):
			for url in urls:
				assert isinstance(url, str)
		else:
			urls = [urls]

		self.allResourcesDirectory = allResourcesDirectory
		self.workingDirectory = workingDirectory

		self.downloadDirectory = os.path.join(allResourcesDirectory,name)

		self.name = name
		self.urls = urls
		#self.dirName = dirName
		#self.sourceFormat = sourceFormat
		#self.projectFormat = projectFormat
		#self.removePMCOADuplicates = removePMCOADuplicates
		#self.usePubmedHashes = usePubmedHashes
		#self.pmids = pmids
		#self.pmcids = pmcids

		#packagePath = os.path.dirname(pubrunner.__file__)
		#pubrunnerResourcePath = os.path.join(packagePath,'resources','%s.yml' % sourceName)
		#projectResourcePath = os.path.join('resources','%s.yml' % sourceName)

		#options = [projectResourcePath,pubrunnerResourcePath]
		#options = [ f for f in options if os.path.isfile(f) ]
		#assert len(options) > 0, "Unable to find resource YAML file for resource: %s" % sourceName
		#with open(options[0]) as f:
		#	resourceInfo = yaml.load(f)

		#self.sourceFormat = resourceInfo['sourceFormat']
		#self.chunkSize = resourceInfo['chunkSize'] if 'chunkSize' in resourceInfo else 1


	def convert(self):
		if self.sourceFormat == self.projectFormat:
			return

	def download(self):
		if not os.path.isdir(self.downloadDirectory):
			os.makedirs(self.downloadDirectory)

		for url in self.urls:
			if False: #sourceName == 'PUBMED_CUSTOM':
				for pmid in self.pmids:
					filename = os.path.join(dirToCreate,'%d.xml' % pmid)
					eutilsToFile('pubmed',pmid,filename)
			elif False: #sourceName == 'PMCOA_CUSTOM':
				for pmcid in pmcids:
					filename = os.path.join(dirToCreate,'%d.nxml' % pmcid)
					eutilsToFile('pmc',pmcid,filename)
			elif url.startswith('https://github.com'):
				assert isinstance(resourceInfo['url'], six.string_types), 'The URL for a git resource must be a single address'

				if os.path.isdir(thisResourceDir):
					# Assume it is an existing git repo
					repo = git.Repo(thisResourceDir)
					repo.remote().pull()
				else:
					os.makedirs(thisResourceDir)
					git.Repo.clone_from(resourceInfo["url"], thisResourceDir)
				
				#generateFileListing(thisResourceDir)

				return thisResourceDir
			elif url.startswith('https://zenodo.org/record/'):
				recordNo = int(url[len('https://zenodo.org/record/'):])

				print("  Starting Zenodo download...")
				pubrunner.download.downloadZenodo(recordNo,self.downloadDirectory)

			else:
				#if 'filter' in resourceInfo:
				#	fileSuffixFilter = resourceInfo['filter']
				#else:
				#	fileSuffixFilter = None


				print("  Starting download...")
				basename = url.split('/')[-1]
				pubrunner.download.download(url,os.path.join(self.downloadDirectory,basename),None) #fileSuffixFilter)

				#if 'unzip' in resourceInfo and resourceInfo['unzip'] == True:
				#	print("  Unzipping archives...")
				#	for filename in os.listdir(thisResourceDir):
				#		if filename.endswith('.tar.gz') or filename.endswith('.tgz'):
				#			tar = tarfile.open(os.path.join(thisResourceDir,filename), "r:gz")
				#			tar.extractall(thisResourceDir)
				#			tar.close()
				#		elif filename.endswith('.gz'):
				#			unzippedName = filename[:-3]
				#			gunzip(os.path.join(thisResourceDir,filename), os.path.join(thisResourceDir,unzippedName), deleteSource=True)

				#if not fileSuffixFilter is None:
				#	print("  Removing files not matching filter (%s)..." % fileSuffixFilter)
			
				#	for root, subdirs, files in os.walk(thisResourceDir):
				#		for f in files:
				#			if not f.endswith(fileSuffixFilter):
				#				fullpath = os.path.join(root,f)
				#				os.unlink(fullpath)

				#if 'generatePubmedHashes' in resourceInfo and resourceInfo['generatePubmedHashes'] == True:
				#	print("  Generating Pubmed hashes...")
				#	hashDir = os.path.join(resourceDir,resource+'.hashes')
				#	if not os.path.isdir(hashDir):
				#		os.makedirs(hashDir)

				#	generatePubmedHashes(thisResourceDir,hashDir)

				#generateFileListing(thisResourceDir)


	def fetch(self):
		self.download()
		self.convert()

	#def downloadDireco
