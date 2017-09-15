import argparse

def main():
	parser = argparse.ArgumentParser(description='Tool to convert corpus between different formats')
	parser.add_argument('--i',type=str,required=True,help="Document or directory of documents to convert")
	parser.add_argument('--iFormat',type=str,required=True,help="Format of input corpus")
	parser.add_argument('--o',type=str,required=True,help="Where to store resulting converted docs")
	parser.add_argument('--oFormat',type=str,required=True,help="Format for output corpus")

	args = parser.parse_args()

	inFormat = args.iFormat.lower()
	outFormat = args.oFormat.lower()

	assert inFormat == 'pubmedxml'
	assert outFormat == 'bioc'

	doc = loadDoc(args.i)

