import pubrunner
import os
import pyfiglet
#import termcolor
#from cursesmenu import *
#from cursesmenu.items import *
import sys


trackLines = 0
def myprint(text="",clear=False,end='\n'):
	global trackLines

	if clear:
		for _ in range(trackLines+1):
			#sys.stdout.write("\033[K")
			CURSOR_UP_ONE = '\x1b[1A'
			ERASE_LINE = '\x1b[2K'
			print(CURSOR_UP_ONE + ERASE_LINE + CURSOR_UP_ONE)
		trackLines = 0

	trackLines += len(text.split('\n'))
	print(text,end=end)
	


def prompt(prompt='> ', accepted=None):
	while True:
		myprint(prompt,end='')
		sys.stdout.flush()
		userinput = sys.stdin.readline().strip()
		if accepted is None or userinput in accepted:
			break
		else:
		 	print("Input not allowed. Must be one of %s" % str(accepted))
	return userinput

def promptAbsPath(prompt='> '):
	while True:
		myprint(prompt,end='')
		sys.stdout.flush()
		userinput = sys.stdin.readline().strip()
		if os.path.isabs(userinput):
			break
		else:
		 	print("Input must be an absolute path")
	return userinput


def setupStorage(globalSettings):
	myprint("###################",clear=True)
	myprint("# Storage options #")
	myprint("###################")
	myprint()
	myprint("These locations are where resources (e.g. PubMed) and intermediate files for the different projects will be stored. These files can be very large.")
	myprint()
	myprint("1) resources: %s" % globalSettings['storage']['resources'])
	myprint("2) workspace: %s" % globalSettings['storage']['workspace'])
	myprint()
	myprint("Type a number to change the value for that or just ENTER to move on")
	response = prompt(accepted=['1','2',''])
	myprint(response)

	if response == '1':
		print("Type the location for resources")
		globalSettings['storage']['resources'] = promptAbsPath()
		setupStorage(globalSettings)
	elif response == '2':
		print("Type the location for workspace")
		globalSettings['storage']['workspace'] = promptAbsPath()
		setupStorage(globalSettings)

def wizard():
	print(pyfiglet.figlet_format('PubRunner', font='cyberlarge', justify='center'))
	print(pyfiglet.figlet_format('Wizard', font='cybermedium', justify='center'))

	homeDirectory = os.path.expanduser("~")
	globalSettingsPath = os.path.join(homeDirectory,'.pubrunner.settings.yml')

	if not os.path.isfile(globalSettingsPath):
		pass

	globalSettings = pubrunner.loadYAML(globalSettingsPath)

	setupStorage(globalSettings)

	#def optionHandler():
	#	print(100)
	#	assert False

	#title = pyfiglet.figlet_format('PubRunner', font='cyberlarge', justify='center')

	#menu = CursesMenu("PubRunner Wizard: Main Menu",title,show_exit_option=True)
	#menu_item = MenuItem("Menu Item")
	#menu.append_item(menu_item)
	#menu.show()
