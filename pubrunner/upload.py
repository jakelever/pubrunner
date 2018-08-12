import pubrunner
import os
import shutil
import requests
import json
import markdown2

def pushToFTP(outputList,toolSettings,globalSettings):
	FTP_ADDRESS = globalSettings["upload"]["ftp"]["url"]
	FTP_USERNAME = globalSettings["upload"]["ftp"]["username"]
	FTP_PASSWORD = globalSettings["upload"]["ftp"]["password"]
	# N.B. This doesn't recursively copy files

	# Push output folder contents
	# 1. Set up FTP
	ftpc = pubrunner.FTPClient(FTP_ADDRESS, FTP_USERNAME, FTP_PASSWORD)
	# 2. Go the the right directory, or create it
	ftpc.cdTree(toolSettings["name"]+"/"+str(toolSettings["version"])+"/")

	assert len(outputList) == 1 and os.path.isdir(outputList[0]), "FTP only accepted a single output directory at the moment"
	outputDir = outputList[0]
	for f in os.listdir(outputDir):
		fPath = os.path.join(outputDir, f)
		if os.path.isfile(fPath):
			ftpc.upload(outputDir, f)

	# 4. Close session
	ftpc.quit()

def pushToLocalDirectory(outputList,toolSettings,globalSettings):
	LOCAL_DIRECTORY = os.path.expanduser(globalSettings["upload"]["local-directory"]["path"])

	destDir = os.path.join(LOCAL_DIRECTORY,toolSettings["name"],str(toolSettings["version"]))
	if not os.path.isdir(destDir):
		os.makedirs(destDir)

	for src in outputList:
		basename = os.path.basename(src)
		dst = os.path.join(destDir, basename)
		if os.path.isfile(src):
			shutil.copyfile(src,dst)
		elif os.path.isdir(src):
			if os.path.isdir(dst):
				shutil.rmtree(dst)
			shutil.copytree(src,dst)

def pushToZenodo(outputList,toolSettings,globalSettings):
	for f in outputList:
		assert os.path.isfile(f) or os.path.isdir(f), "Output (%s) was not found. It must be a file or directory." % f

	if "sandbox" in globalSettings["upload"]["zenodo"] and globalSettings["upload"]["zenodo"]["sandbox"] == True:
		ZENODO_URL = 'https://sandbox.zenodo.org'
	else:
		ZENODO_URL = 'https://zenodo.org'

	ZENODO_AUTHOR = globalSettings["upload"]["zenodo"]["author"]
	ZENODO_AUTHOR_AFFILIATION = globalSettings["upload"]["zenodo"]["authorAffiliation"]

	ACCESS_TOKEN = globalSettings["upload"]["zenodo"]["token"]

	headers = {"Content-Type": "application/json"}

	if "zenodo" in toolSettings:
		existingZenodoID = int(toolSettings["zenodo"])

		print("  Creating new version of Zenodo submission %d" % existingZenodoID)

		r = requests.get(ZENODO_URL + '/api/records/%d' % existingZenodoID, json={}, headers=headers)
		assert r.status_code == 200, 'Unable to find existing Zenodo record %d to update' % existingZenodoID

		# Update with the latest ID
		existingZenodoID = r.json()['id']

		# https://github.com/zenodo/zenodo/issues/954
		# /api/deposit/newversion?recid=134 vs /api/deposit/123/actions/newversion

		r = requests.post(ZENODO_URL + '/api/deposit/depositions/%d/actions/newversion' % existingZenodoID,
							params={'access_token': ACCESS_TOKEN}, json={},
							headers=headers)

		assert r.status_code == 201, 'Unable to create new version of Zenodo record %d' % existingZenodoID

		jsonResponse = r.json()
		newversion_draft_url = r.json()['links']['latest_draft']
		deposition_id = newversion_draft_url.split('/')[-1] 

		r = requests.get(ZENODO_URL + '/api/deposit/depositions/%s' % deposition_id, params={'access_token':ACCESS_TOKEN})

		assert r.status_code == 200, 'Unable to find Zenodo record %s' % deposition_id

		bucket_url = r.json()['links']['bucket']
		doi = r.json()["metadata"]["prereserve_doi"]["doi"]
		doiURL = "https://doi.org/" + doi
	
		print("  Clearing old files from new version of %d" % existingZenodoID)
		for f in r.json()['files']:
			file_id = f['id']
			r = requests.delete(ZENODO_URL + '/api/deposit/depositions/%s/files/%s' % (deposition_id,file_id), params={'access_token': ACCESS_TOKEN})

			assert r.status_code == 204, 'Unable to clear old files in Zenodo record %s' % deposition_id

		print("  Got provisional DOI: %s" % doiURL)
	else:
		print("  Creating new Zenodo submission")
		r = requests.post(ZENODO_URL + '/api/deposit/depositions',
						params={'access_token': ACCESS_TOKEN}, json={},
						headers=headers)

		assert r.status_code == 201, "Unable to create Zenodo submission (error: %d) " % r.status_code

		bucket_url = r.json()['links']['bucket']
		deposition_id = r.json()['id']
		doi = r.json()["metadata"]["prereserve_doi"]["doi"]
		doiURL = "https://doi.org/" + doi

		print("  Got provisional DOI: %s" % doiURL)

	print("  Adding files to Zenodo submission")
	if len(outputList) > 1:
		for f in outputList:
			assert not os.path.isdir(f), "If output includes a directory, it must be the only output"

	# Replace output list with directory listing
	if os.path.isdir(outputList[0]):
		outputDir = outputList[0]
		outputList = [ os.path.join(outputDir, f) for f in os.listdir(outputDir) ]

	for f in outputList:
		assert os.path.isfile(f), "Cannot upload non-file (%s) to Zenodo" % f
		basename = os.path.basename(f)

		r = requests.put('%s/%s' % (bucket_url,basename),
						data=open(f, 'rb'),
						headers={"Accept":"application/json",
						"Authorization":"Bearer %s" % ACCESS_TOKEN,
						"Content-Type":"application/octet-stream"})

		assert r.status_code == 200, "Unable to add file to Zenodo submission (error: %d) " % r.status_code

	description = 'Results from %s tool executed using PubRunner' % toolSettings['name']
	if "output_description_file" in toolSettings:
		output_description_file = toolSettings["output_description_file"]
		assert os.path.isfile(output_description_file), "Unable to find output_description_file (%s)" % output_description_file
		with open(output_description_file) as f:
			description = f.read().strip()

		if output_description_file.endswith('.md'):
			description = markdown2.markdown(description)
	elif "output_description" in toolSettings:
		description = toolSettings["output_description"]

	print("  Adding metadata to Zenodo submission")
	data = {
			'metadata': {
					'title': toolSettings['name'],
					'upload_type': 'dataset',
					'description':	description,
					'creators': [{'name': ZENODO_AUTHOR,
							'affiliation': ZENODO_AUTHOR_AFFILIATION}]
			}
	}

	r = requests.put(ZENODO_URL + '/api/deposit/depositions/%s' % deposition_id,
					params={'access_token': ACCESS_TOKEN}, data=json.dumps(data),
					headers=headers)

	assert r.status_code == 200, "Unable to metadata to Zenodo submission (error: %d) " % r.status_code

	print("  Publishing Zenodo submission")
	r = requests.post(ZENODO_URL + '/api/deposit/depositions/%s/actions/publish' % deposition_id,
					 params={'access_token': ACCESS_TOKEN} )
	assert r.status_code == 202, "Unable to publish to Zenodo submission (error: %d) " % r.status_code

	return doiURL

