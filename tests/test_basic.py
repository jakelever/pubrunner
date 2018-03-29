import sys
import pubrunner
import pubrunner.command_line
import os
import time

def test_countwords():
	parentDir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
	projectPath = os.path.join(parentDir,'examples','CountWords')
	sys.argv = ['pubrunner', '--defaultsettings', '--test',projectPath]
	pubrunner.command_line.main()
	time.sleep(1)

def test_textminingcounter():
	parentDir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
	projectPath = os.path.join(parentDir,'examples','TextMiningCounter')
	sys.argv = ['pubrunner', '--defaultsettings', '--test',projectPath]
	pubrunner.command_line.main()
	time.sleep(1)

