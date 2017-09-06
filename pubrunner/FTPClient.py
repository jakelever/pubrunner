from ftplib import FTP
import os

class FTPClient:

	def __init__(self, address, user, passw):
		self.ftp = FTP(address, user, passw)

	# Walk up the tree and make directories when needed
	def cdTree(self, currentDir):
		currentDir = currentDir.rstrip('/')
		subdirs = currentDir.split('/')
		for subdir in subdirs:
			try:
				self.ftp.cwd(subdir)
			except:
				self.ftp.mkd(subdir)
				self.ftp.cwd(subdir)

	def upload(self, path, filename):
		fh = open(os.path.join(path, filename),'rb')
		self.ftp.storbinary('STOR '+filename, fh)
		fh.close()

	def quit(self):
		self.ftp.quit()
