import sys
import os
import shutil
import pubrunner

# https://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks
def chunks(l, n):
	"""Yield successive n-sized chunks from l."""
	for i in range(0, len(l), n):
		yield l[i:i + n]

def findFiles(dirName):
	allFiles = []
	for root, dirs, files in os.walk(dirName):
		allFiles += [ os.path.join(root,f) for f in files ]
	
	# We're going to extract the last set of digits from each filename and sort by that
	nums = [ re.findall('[0-9]+',f) for f in allFiles ]
	nums = [ 0 if num == [] else int(num[-1]) for num in nums ]
	sortedByNum = sorted(list(zip(nums,allFiles)))
	sortedFilepaths = [ filepath for num,filepath in sortedByNum ]
	
	return sortedFilepaths

snakemakeExec = shutil.which('snakemake')

requiredEnvironmentalVariables = ["INDIR","OUTDIR"]
missingVariables = []
for v in requiredEnvironmentalVariables:
	if os.environ.get(v) is None:
		missingVariables.append(v)

if not missingVariables == []:
	print("ERROR: Missing required environmental variables: %s" % (str(missingVariables)))
	print("This Snakefile uses environmental variables as input parameters")
	print()
	print("Example usage:")
	print("  INDIR=PUBMED OUTDIR=PUBMED.hashes snakemake -s %s" % __file__)
	print()
	print("  INDIR is the input directory of the Pubmed resource")
	print("  OUTDIR is the output directory for the hash data")
	sys.exit(1)

inDir = os.environ.get("INDIR")
outDir = os.environ.get("OUTDIR")
chunkSize = 5

inAndOut = []
for f in findFiles(inDir):
	if f.endswith('.xml'):
		outFile = f.replace(inDir,outDir) + '.hashes'
		if not os.path.isdir(os.path.dirname(outFile)):
			os.makedirs(os.path.dirname(outFile))
		inAndOut.append((f,outFile))

allOutFiles = [ outFile for inFile,outFile in inAndOut ]

localrules: all

rule all:
	input: allOutFiles

for chunk in chunks(inAndOut,chunkSize):
	rule:
		input: [ inFile for inFile,outFile in chunk ]
		output: [ outFile for inFile,outFile in chunk ]
		run:
			for inFile,outFile in zip(input,output):
				pubrunner.pubmed_hash(inFile,outFile)

