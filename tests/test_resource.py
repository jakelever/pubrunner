import pubrunner

def test_download():
	resource = pubrunner.Resource(sourceName='PUBMED_README')
	resource.download()

	directory = resource.getDownloadDirectory()

	expectedMD5s = {}
	for f in os.listdir(directory):
		md5sum = calcMD5(os.path.join(directory,f))
		assert f in expectedMD5s
		assert md5sum == expectedMD5s[f]

def test_convert():
	resource = pubrunner.Resource(sourceName='PUBMED_README',requiredFormat='biocxml')
	resource.download()
	resource.convert()

	directory = resource.getDirectory()

	expectedMD5s = {}
	for f in os.listdir(directory):
		md5sum = calcMD5(os.path.join(directory,f))
		assert f in expectedMD5s
		assert md5sum == expectedMD5s[f]
	
