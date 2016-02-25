#An EXTREMELY basic client for W.I.L.L., mainly used for light debugging
import easygui
import urllib
import sys
def main(command):
	'''A basic debugging oriented client using easygui'''
	command=urllib.urlencode({"command":command})
	answer=urllib.urlopen("http://127.0.0.1:5000?context=command&%s"%command).read()
	easygui.msgbox(answer)
while True:
	command=easygui.enterbox(title="W.I.L.L.", msg="Please enter a command")
	if command=="exit":
		sys.exit()
	elif command==None:
		sys.exit()
	else:
		main(command)
