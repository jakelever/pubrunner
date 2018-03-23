import sys
import pubrunner
import pubrunner.command_line

def test_countwords():
	#pubrunner.pubrun('examples/CountWords/',True,True)
	sys.argv = ['pubrunner', '--defaultsettings', '--test','examples/CountWords/']
	pubrunner.command_line.main()

def test_textminingcounter():
	#pubrunner.pubrun('examples/CountWords/',True,True)
	sys.argv = ['pubrunner', '--defaultsettings', '--test','examples/TextMiningCounter/']
	pubrunner.command_line.main()
