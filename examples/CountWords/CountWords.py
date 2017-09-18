import argparse
import xml.etree.cElementTree as etree
import os
from os import listdir
from os.path import isfile, join

def processMedlineFolder(medlineFolder,outFolder):
	"""Basic function that iterates through abstracts in a medline file, do a basic word count and save to a file

	Args:
		medlineFolder (folder): Medline XML folder containing abstracts
		outFolder (folder): Folder to save output data to
	Returns:
		Nothing

	"""
	abstractCount = 0

	# List of all files in the directory
	files = [ f for f in listdir(medlineFolder) if isfile(join(medlineFolder, f)) ]
	
	# Filter for only XML files
	files = [ f for f in files if f.endswith('xml') ]

	with open(os.path.join(outFolder,"countWords.txt"), "a") as result:
		# Iterate over all files
		for f in files:
			print("Processing %s" % f)
			# Iterate through the XML file and stop on each MedlineCitation
			for event, elem in etree.iterparse(os.path.join(medlineFolder,f), events=('start', 'end', 'start-ns', 'end-ns')):
				if (event=='end' and elem.tag=='MedlineCitation'):

					# Let's get the PMID and Abstract elements from the XML
					pmidElements = elem.findall('./PMID')
					abstractElements = elem.findall('./Article/Abstract/AbstractText')

					if len(pmidElements) != 1 or len(abstractElements) != 1:
						continue

					# Pull the values of the PMID and abstract elements
					pmid = pmidElements[0].text
					abstract = abstractElements[0].text

					if not abstract is None:
						# Do a very basic word count
						wordCount = len(abstract.split())

						# Prepare and save output to file
						line = "%s\t%d\n" % (pmid,wordCount)

						result.write(line)

						abstractCount += 1

	print("%d abstracts processed" % abstractCount)

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Little toy example to "process" a Medline abstract file and gives naive word counts for each abstract')
	parser.add_argument('-i',required=True,help='Medline folder to process')
	parser.add_argument('-o',required=True,help='Output folder for word-counts')

	args = parser.parse_args()

	if not os.path.isdir(args.o):
		os.makedirs(args.o)

	processMedlineFolder(args.i,args.o)
