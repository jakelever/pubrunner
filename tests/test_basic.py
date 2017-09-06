import sys
import pubrunner
from pubrunner.command_line import main

def test_countwords():
	sys.argv = ['pubrunner', '--test', 'tests/testrepos/CountWords/']
	main()
	# Check that things have happened

