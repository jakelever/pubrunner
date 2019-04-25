
import os
from Bio import Entrez
import git

import pubrunner.download

def eutilsToFile(email,db,id,filename):
	Entrez.email = email
	handle = Entrez.efetch(db=db, id=id, rettype="gb", retmode="xml")
	with open(filename,'w') as f:
		xml = handle.read()
		f.write(xml)

class Resource:
	def __init__(self,allResourcesDirectory,workingDirectory,name,urls,email=None):#,name,sourceFormat,projectFormat,removePMCOADuplicates,usePubmedHashes,pmids,pmcids):
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

		assert email is None or isinstance(email, str)

		self.allResourcesDirectory = allResourcesDirectory
		self.workingDirectory = workingDirectory

		self.downloadDirectory = os.path.join(allResourcesDirectory,name)

		self.name = name
		self.urls = urls
		self.email = email

	def download(self):
		if not os.path.isdir(self.downloadDirectory):
			os.makedirs(self.downloadDirectory)

		for url in self.urls:
			if url.startswith('https://www.ncbi.nlm.nih.gov/pubmed/'):
				assert self.email is not None, "Must provide email address to use NCBI EUtils to download a PubMed abstract"

				pmid = int(url[len('https://www.ncbi.nlm.nih.gov/pubmed/'):])
				filename = os.path.join(self.downloadDirectory,'pubmed_%d.xml' % pmid)
				eutilsToFile(self.email,'pubmed',pmid,filename)
			elif url.startswith('https://www.ncbi.nlm.nih.gov/pmc/'):
				assert self.email is not None, "Must provide email address to use NCBI EUtils to download a PMC article"
				
				pmcid = int(url[len('https://www.ncbi.nlm.nih.gov/pmc/'):])
				filename = os.path.join(self.downloadDirectory,'pmc_%d.nxml' % pmcid)
				eutilsToFile(self.email,'pmc',pmcid,filename)
			elif url.startswith('https://github.com'):
				#try:
					# Assume it is an existing git repo
				#	repo = git.Repo(thisResourceDir)
				#	repo.remote().pull()
				#except:
				#	pass

				git.Repo.clone_from(url, self.downloadDirectory)
			
			elif url.startswith('https://zenodo.org/record/'):
				recordNo = int(url[len('https://zenodo.org/record/'):])

				print("  Starting Zenodo download...")
				pubrunner.download.downloadZenodo(recordNo,self.downloadDirectory)

			else:
				print("  Starting download...")
				basename = url.split('/')[-1]
				pubrunner.download.download(url,os.path.join(self.downloadDirectory,basename),None) #fileSuffixFilter)

