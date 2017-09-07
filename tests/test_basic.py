import sys
import pubrunner

def test_countwords():
	#sys.argv = ['pubrunner', '--test', 'tests/testrepos/CountWords/']
	#pubrunner.main()
	pubrunner.pubrun('tests/testrepos/CountWords/',True)
	# Check that things have happened

