import sys
import argparse
import pubrunner

class PubRunnerMain(object):

	def __init__(self):
		parser = argparse.ArgumentParser(
			description='PubRunner will manage the download of needed resources for a text mining tool, build and execute it and then share the results publicly',
			usage='''pubrunner <command> [<args>]

The most commonly used pubrunner commands are:
convert    Convert a biomedical corpus from one format to another
clean      Clean the working directory of the current project
fetch      Update biomedical resources (e.g. PubMed)
run        Start a PubRunner run for a project
publish    Publish the output files of a PubRunner run to external hosting
settings   Edit global or project-specific PubRunner settings
''')

		parser.add_argument('command', help='Subcommand to run')
		# parse_args defaults to [1:] for args, but you need to
		# exclude the rest of the args too, or validation will fail
		args = parser.parse_args(sys.argv[1:2])
		if not hasattr(self, args.command):
			print('Unrecognized command')
			parser.print_help()
			exit(1)

		# use dispatch pattern to invoke method with same name
		getattr(self, args.command)()

	def convert(self):
		acceptedInFormats = ['biocxml','pubmedxml','marcxml','pmcxml','uimaxmi']
		acceptedOutFormats = ['biocxml','txt']

		parser = argparse.ArgumentParser(prog='pubrunner convert',
				description='Convert a biomedical corpus from one format to another')
		parser.add_argument('--i',type=str,required=True,help="Comma-delimited list of documents to convert")
		parser.add_argument('--iFormat',type=str,required=True,help="Format of input corpus. Options: %s" % "/".join(acceptedInFormats))
		parser.add_argument('--idFilters',type=str,help="Optional set of ID files to filter the documents by")
		parser.add_argument('--o',type=str,required=True,help="Where to store resulting converted docs")
		parser.add_argument('--oFormat',type=str,required=True,help="Format for output corpus. Options: %s" % "/".join(acceptedOutFormats))

		args = parser.parse_args(sys.argv[2:])

		inFormat = args.iFormat.lower()
		outFormat = args.oFormat.lower()

		assert inFormat in acceptedInFormats, "%s is not an accepted input format. Options are: %s" % (inFormat, "/".join(acceptedInFormats))
		assert outFormat in acceptedOutFormats, "%s is not an accepted output format. Options are: %s" % (outFormat, "/".join(acceptedOutFormats))

		inFiles = args.i.split(',')
		if args.idFilters:
			idFilterfiles = args.idFilters.split(',')
			assert len(inFiles) == len(idFilterfiles), "There must be the same number of input files as idFilters files"
		else:
			idFilterfiles = None

		pubrunner.convertFiles(inFiles,inFormat,args.o,outFormat,idFilterfiles)

	def clean(self):
		parser = argparse.ArgumentParser(prog='pubrunner clean',
				description='Clean the working directory of the current project')
		parser.add_argument('--test',action='store_true',help='Whether to use the test version of this project')
		args = parser.parse_args(sys.argv[2:])

		pubrunner.cleanWorkingDirectory('.',args.test)

	def run(self):
		parser = argparse.ArgumentParser(prog='pubrunner run',
				description='Start a PubRunner run for a project')
		parser.add_argument('--test',action='store_true',help='Whether to use the test version and working directory for this project')
		#parser.add_argument('--local',action='store_true',help='Ignore any cluster settings and run everything locally')
		#parser.add_argument('--update',action='store_true',help='Update all the resources (e.g. PubMed) that this project uses before doing the run')
		args = parser.parse_args(sys.argv[2:])

		pubrunner.pubrun('.',args.test)

	def fetch(self):
		parser = argparse.ArgumentParser(prog='pubrunner fetch',
				description='Download the latest version of biomedical resources (e.g. PubMed)')
		parser.add_argument('--test',action='store_true',help='Whether to use the test version and working directory for this project')
		args = parser.parse_args(sys.argv[2:])

	def publish(self):
		parser = argparse.ArgumentParser(prog='pubrunner publish',
				description='Publish the results of a project to a repository')
		args = parser.parse_args(sys.argv[2:])

	def settings(self):
		parser = argparse.ArgumentParser(prog='pubrunner settings',
				description='Launch an editor for the global or project-specific settings')
		args = parser.parse_args(sys.argv[2:])


def main():
	PubRunnerMain()

