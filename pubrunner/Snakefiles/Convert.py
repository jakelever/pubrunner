import sys
import os
import re
import json
from collections import Counter,defaultdict
import pubrunner
import shutil

snakemakeExec = shutil.which('snakemake')

requiredEnvironmentalVariables = ["CHUNKDIR","OUTDIR","INFORMAT","OUTFORMAT"]
missingVariables = []
for v in requiredEnvironmentalVariables:
	if os.environ.get(v) is None:
		missingVariables.append(v)

if not missingVariables == []:
	print("ERROR: Missing required environmental variables: %s" % (str(missingVariables)))
	print("This Snakefile uses environmental variables as input parameters")
	print()
	print("Example usage:")
	print("  OUTDIR=OUT CHUNKDIR=CHUNKS [PMIDCHUNKDIR=PMIDDIR] snakemake -s %s" % __file__)
	print()
	print("  OUTDIR is the output directory for the conversion")
	print("  CHUNKDIR is a directory of JSON files with lists of input files")
	print("  INFORMAT is the input format (e.g. pubmedxml, pmcxml, marcxml, etc)")
	print("  OUTFORMAT is the output format for the converted data (e.g. bioc, txt)")
	print("  PMIDCHUNKDIR is an optional argument that gives a directory containing PMIDs file listings corresponding to the CHUNKDIR")
	sys.exit(1)

chunkDir = os.environ.get("CHUNKDIR")
outDir = os.environ.get("OUTDIR")
inFormat = os.environ.get("INFORMAT")
outFormat = os.environ.get("OUTFORMAT")
pmidChunkDir = os.environ.get("PMIDCHUNKDIR")

chunkFiles = list(os.listdir(chunkDir))
inputFiles = [ os.path.join(chunkDir,f) for f in chunkFiles ]
outputFiles = [ os.path.join(outDir,f) for f in chunkFiles ]

if pmidChunkDir:
	pmidChunkFiles = [ os.path.join(pmidChunkDir,f) for f in chunkFiles ]

localrules: all

rule all:
	input: outputFiles

if pmidChunkDir:
	rule convert_with_pmids:
		input: 
			chunkFile=os.path.join(chunkDir,'{filename}'),
			pmidChunkFile=os.path.join(pmidChunkDir,'{filename}')
		output: 
			os.path.join(outDir,'{filename}')
		run: 
			pubrunner.convertFilesFromFilelist(input.chunkFile,inFormat,output[0],outFormat,input.pmidChunkFile)
else:
	rule convert:
		input: 
			os.path.join(chunkDir,'{filename}')
		output: 
			os.path.join(outDir,'{filename}')
		run: 
			pubrunner.convertFilesFromFilelist(input[0],inFormat,output[0],outFormat)

#for inputFile,outputFile in zip(inputFiles,outputFiles):
#	rule:
#		input: inputFile
#		output: outputFile
#		run:
#			pubrunner.convertFilesFromFilelist(input[0],inFormat,output[0],outFormat)
				
