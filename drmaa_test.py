import drmaa
import os

with drmaa.Session() as s:
	jt = s.createJobTemplate()
	jt.remoteCommand = os.path.join(os.getcwd(), 'pytest.py')
	jt.remoteCommand = "python " + os.path.join(os.getcwd(), 'pytest.py')
	jobid = s.runJob(jt)
	s.deleteJobTemplate(jt)

