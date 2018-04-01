import sys
import os
import re
import json
from collections import Counter,defaultdict
import pubrunner
import shutil

snakemakeExec = shutil.which('snakemake')

requiredEnvironmentalVariables = ["CHUNKS","INFORMAT","OUTFORMAT"]
missingVariables = []
for v in requiredEnvironmentalVariables:
	if os.environ.get(v) is None:
		missingVariables.append(v)

if not missingVariables == []:
	print("ERROR: Missing required environmental variables: %s" % (str(missingVariables)))
	print("This Snakefile uses environmental variables as input parameters")
	print()
	print("Example usage:")
	print("  CHUNKS=chunks.json [PMIDDIR=PMIDDIR] snakemake -s %s" % __file__)
	print()
	print("  CHUNKS is a JSON file with a dictionary mapping output converted files names to lists of input files")
	print("  INFORMAT is the input format (e.g. pubmedxml, pmcxml, marcxml, etc)")
	print("  OUTFORMAT is the output format for the converted data (e.g. bioc, txt)")
	print("  PMIDDIR is an optional argument that gives a directory containing PMIDs to include with one file for each file in INDIR")
	sys.exit(1)

chunkFile = os.environ.get("CHUNKS")
inFormat = os.environ.get("INFORMAT")
outFormat = os.environ.get("OUTFORMAT")
pmidDir = os.environ.get("PMIDDIR")

with open(chunkFile) as inF:
	outputFilesWithChunks = json.load(inF)

assignedChunks = {}
for outputFile,chunk in outputFilesWithChunks.items():
	assert isinstance(chunk,list)
	for f in chunk:
		assert not f in assignedChunks
		assignedChunks[f] = outputFile

expectedFiles = sorted(outputFilesWithChunks.keys())

localrules: all

rule all:
	input: expectedFiles

for outputFile,chunk in outputFilesWithChunks.items():
	if pmidDir is None:
		pmidFilterfiles = []
	else:
		baseInputs = [ os.path.basename(f) for f in chunk ]
		pmidFilterfiles = [ os.path.join(pmidDir,f+'.pmids') for f in baseInputs ]
		for f in pmidFilterfiles:
			assert os.path.isfile(f), "Could not find the PMID file: %s" % f
		
	rule:
		input: chunk, pmidFilterfiles = pmidFilterfiles
		output: outputFile
		run:
			inputFileList = list(input)
			outputFile = output[0]
			if pmidDir is None:
				pubrunner.convertFiles(inputFileList,inFormat,outputFile,outFormat)
			else:
				pubrunner.convertFiles(inputFileList,inFormat,outputFile,outFormat,list(input.pmidFilterfiles))
				
