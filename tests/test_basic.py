import sys
import pubrunner
import pubrunner.command_line

def test_countwords():
	#pubrunner.pubrun('examples/CountWords/',True,True)
	sys.argv = ['pubrunner', '--test','examples/CountWords/']
	pubrunner.command_line.main()

