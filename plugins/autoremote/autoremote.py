import urllib2
def main(command):
	f=open("plugins/autoremote/autoremotekey.txt").read()
	if '\n' in f:
		f=f.split('\n')[0]
	urllib2.urlopen('https://autoremotejoaomgcd.appspot.com/sendmessage?key={0}&message={1}'.format(f,command))
	return "Done"
