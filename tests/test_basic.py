import sys
import pubrunner

def test_countwords():
	sys.argv = ['pubrunner', '--test', 'tests/testrepos/CountWords/']
	pubrunner.main()
	# Check that things have happened

