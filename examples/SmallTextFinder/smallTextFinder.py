import argparse
import bioc
import codecs

def findSmallText(biocFilename,tsvFilename):
	with bioc.iterparse(biocFilename) as inBioC, codecs.open(tsvFilename,'w','utf-8') as outTSV:
		# Iterate over every document (Pubmed citation)
		for docCount,biocDoc in enumerate(inBioC):
			# Get some metadata for the citation
			pmid = biocDoc.infons['pmid']
			journal = biocDoc.infons['journal']

			shortArticleSections = [ passage.text for passage in biocDoc.passages if passage.infons['section'] == 'article' and len(passage.text) < 30 ]
		
			for shortArticleSection in shortArticleSections:
				# Save to the file
				output = [pmid,journal,shortArticleSection]
				outTSV.write("\t".join(output) + "\n")

	print("Complete")

if __name__ == '__main__':
	parser = argparse.ArgumentParser('Find small passages that are probably titles')
	parser.add_argument('--inBioC',required=True,type=str,help='Input BioC file to process')
	parser.add_argument('--outTSV',required=True,type=str,help='Output tab-delimited file')
	args = parser.parse_args()

	findSmallText(args.inBioC,args.outTSV)
