import argparse
import xml.etree.ElementTree as ET

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Explore an XML file')
	parser.add_argument('--xmlFile',required=True,type=str,help='XML file to explore')
	args = parser.parse_args()

	tree = ET.parse(args.xmlFile)
	print(dir(tree))
	root = tree.getroot()
	print(dir(root))
	#for c in root.getchildren():
	#	print(c)

	metadataNode = root.find('{http:///de/tudarmstadt/ukp/dkpro/core/api/metadata/type.ecore}DocumentMetaData')
	#print(metadataNode.attrib)
	documentTitle = metadataNode.attrib['documentTitle']
	print(documentTitle)

	contentNode = root.find('{http:///uima/cas.ecore}Sofa')
	content = contentNode.attrib['sofaString']
	print(content)
