
def eutilsToFile(settings,db,id,filename):
	if not 'email' in settings:
		raise RuntimeError("You must provide an email in the global or local settings file")
	Entrez.email = settings['email']
	handle = Entrez.efetch(db=db, id=id, rettype="gb", retmode="xml")
	with codecs.open(filename,'w','utf-8') as f:
		xml = handle.read()
		f.write(xml)

class Resource:
	def __init__(self,sourceName):#,name,sourceFormat,projectFormat,removePMCOADuplicates,usePubmedHashes,pmids,pmcids):
		self.sourceName = sourceName
		#self.dirName = dirName
		#self.sourceFormat = sourceFormat
		#self.projectFormat = projectFormat
		#self.removePMCOADuplicates = removePMCOADuplicates
		#self.usePubmedHashes = usePubmedHashes
		#self.pmids = pmids
		#self.pmcids = pmcids

		packagePath = os.path.dirname(pubrunner.__file__)
		pubrunnerResourcePath = os.path.join(packagePath,'resources','%s.yml' % sourceName)
		projectResourcePath = os.path.join('resources','%s.yml' % sourceName)

		options = [projectResourcePath,pubrunnerResourcePath]
		options = [ f for f in options if os.path.isfile(f) ]
		assert len(options) > 0, "Unable to find resource YAML file for resource: %s" % sourceName
		with open(options[0]) as f:
			resourceInfo = yaml.load(f)

		self.sourceFormat = resourceInfo['sourceFormat']
		self.chunkSize = resourceInfo['chunkSize'] if 'chunkSize' in resourceInfo else 1


	def convert(self):
		if self.sourceFormat == self.projectFormat:
			return

	def download(self):
		if sourceName == 'PUBMED_CUSTOM':
			for pmid in self.pmids:
				filename = os.path.join(dirToCreate,'%d.xml' % pmid)
				eutilsToFile('pubmed',pmid,filename)
		elif sourceName == 'PMCOA_CUSTOM':
			for pmcid in pmcids:
				filename = os.path.join(dirToCreate,'%d.nxml' % pmcid)
				eutilsToFile('pmc',pmcid,filename)
		elif self.resourceType == 'git':
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
		elif self.resourceType == 'zenodo':
			assert isinstance(resourceInfo['record'], int), 'The Zenodo record must be an integer'

			print("  Starting Zenodo download...")
			downloadZenodo(resourceInfo['record'],thisResourceDir)

			return thisResourceDir
		elif self.resourceType == 'remote':
			assert isinstance(resourceInfo['url'], six.string_types) or isinstance(resourceInfo['url'],list), 'The URL for a remote resource must be a single or multiple addresses'
			if isinstance(resourceInfo['url'], six.string_types):
				urls = [resourceInfo['url']]
			else:
				urls = resourceInfo['url']
			
			if 'filter' in resourceInfo:
				fileSuffixFilter = resourceInfo['filter']
			else:
				fileSuffixFilter = None

			if not os.path.isdir(thisResourceDir):
				print("  Creating directory...")
				os.makedirs(thisResourceDir)

			print("  Starting download...")
			for url in urls:
				basename = url.split('/')[-1]
				assert isinstance(url,six.string_types), 'Each URL for the dir resource must be a string'
				download(url,os.path.join(thisResourceDir,basename),fileSuffixFilter)

			if 'unzip' in resourceInfo and resourceInfo['unzip'] == True:
				print("  Unzipping archives...")
				for filename in os.listdir(thisResourceDir):
					if filename.endswith('.tar.gz') or filename.endswith('.tgz'):
						tar = tarfile.open(os.path.join(thisResourceDir,filename), "r:gz")
						tar.extractall(thisResourceDir)
						tar.close()
					elif filename.endswith('.gz'):
						unzippedName = filename[:-3]
						gunzip(os.path.join(thisResourceDir,filename), os.path.join(thisResourceDir,unzippedName), deleteSource=True)

			if not fileSuffixFilter is None:
				print("  Removing files not matching filter (%s)..." % fileSuffixFilter)
				for root, subdirs, files in os.walk(thisResourceDir):
					for f in files:
						if not f.endswith(fileSuffixFilter):
							fullpath = os.path.join(root,f)
							os.unlink(fullpath)

			if 'generatePubmedHashes' in resourceInfo and resourceInfo['generatePubmedHashes'] == True:
				print("  Generating Pubmed hashes...")
				hashDir = os.path.join(resourceDir,resource+'.hashes')
				if not os.path.isdir(hashDir):
					os.makedirs(hashDir)

				generatePubmedHashes(thisResourceDir,hashDir)

			#generateFileListing(thisResourceDir)

			return thisResourceDir
		elif self.resourceType == 'local':
			assert isinstance(resourceInfo['directory'], six.string_types) and os.path.isdir(resourceInfo['directory']), 'The directory for a remote resource must be a string and exist'

			if not os.path.islink(thisResourceDir) and os.path.isdir(thisResourceDir):
				shutil.rmtree(thisResourceDir)

			if not os.path.islink(thisResourceDir):
				os.symlink(resourceInfo['directory'],thisResourceDir)
		else:
			raise RuntimeError("Unknown resource type (%s) for resource: %s" % (self.resourceType,self.sourceName))

	def fetch(self):
		self.download()
		self.convert()

	#def downloadDireco
