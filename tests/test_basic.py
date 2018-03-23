import sys
import pubrunner
import pubrunner.command_line

def test_countwords():
	parentDir = os.path.dirname(os.path.abspath(__file__))
	projectPath = os.path.join(parentDir,'examples','CountWords')
	sys.argv = ['pubrunner', '--defaultsettings', '--test',projectPath]
	pubrunner.command_line.main()

def test_textminingcounter():
	parentDir = os.path.dirname(os.path.abspath(__file__))
	projectPath = os.path.join(parentDir,'examples','TextMiningCount')
	sys.argv = ['pubrunner', '--defaultsettings', '--test',projectPath]
	pubrunner.command_line.main()

