#In development
import spotify
config = spotify.Config()
config.user_agent = 'W.I.L.L'
session = spotify.Session()
def play(command):

	loop = spotify.EventLoop(session)
	loop.start()

	# Connect an audio sink
	audio = spotify.AlsaSink(session)

	# Events for coordination
	logged_in = threading.Event()
	end_of_track = threading.Event()


	def on_connection_state_updated(session):
	    if session.connection.state is spotify.ConnectionState.LOGGED_IN:
	        logged_in.set()


	def on_end_of_track(self):
	    end_of_track.set()


	# Register event listeners
	session.on(
	    spotify.SessionEvent.CONNECTION_STATE_UPDATED, on_connection_state_updated)
	session.on(spotify.SessionEvent.END_OF_TRACK, on_end_of_track)

	# Assuming a previous login with remember_me=True and a proper logout
	session.relogin()

	logged_in.wait()
	commandl=command.split(" ")
	triggers=['spotify','play']
	triggerword=None
	for word in commandl:
		for trigger in triggers:
			if word.lower()==trigger:
				triggerword=word
			else:
				pass
	if triggerword==None:
		return "trigger word not found"
	else:
		searchterm=command.split(triggerword)
	search = session.search(searchterm)
	search = session.search(searchterm, search_type=spotify.SearchType.SUGGEST).load()
	playitem=None
	if len(search.tracks) > 0:
		playitem=search.tracks[0]
		track = session.get_track(track_uri).load()
		session.player.load(track)
		session.player.play()

		# Wait for playback to complete or Ctrl+C
		try:
		    while not end_of_track.wait(0.1):
		        pass
		except KeyboardInterrupt:
		    pass
