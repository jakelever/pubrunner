import argparse
import bioc
import codecs

def convertBioC2TSV(biocFilename,tsvFilename):
	with bioc.iterparse(biocFilename) as inBioC, codecs.open(tsvFilename,'w','utf-8') as outTSV:
		# Output the headers to the TSV file
		headers = ['pmid','year','title','abstract']
		outTSV.write("\t".join(headers) + "\n")

		# Iterate over every document (Pubmed citation)
		for docCount,biocDoc in enumerate(inBioC):
			# Get some metadata for the citation
			pmid = biocDoc.infons['pmid']
			year = biocDoc.infons['year']
			title = biocDoc.infons['title']

			# Get the abstract text
			abstract = [ passage.text for passage in biocDoc.passages if passage.infons['section'] == 'abstract' ]
			if len(abstract) > 0:
				abstract = " ".join(abstract).replace('\n','').replace('\r','')
			else:
				abstract = ""
			
			# Save to the file
			output = [pmid,year,title,abstract]
			outTSV.write("\t".join(output) + "\n")

			if ((docCount+1) % 1000) == 0:
				print("Processed %d documents..." % (docCount+1))

	print("Complete")

if __name__ == '__main__':
	parser = argparse.ArgumentParser('Converts BioC to a tab-delimited format')
	parser.add_argument('--inBioC',required=True,type=str,help='Input BioC file to convert')
	parser.add_argument('--outTSV',required=True,type=str,help='Output tab-delimited file')
	args = parser.parse_args()

	convertBioC2TSV(args.inBioC,args.outTSV)
