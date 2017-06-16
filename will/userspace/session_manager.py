#Builtin imports
import threading
import logging
import time
import queue

# Internal imports
from will.userspace import sessions

log = logging.getLogger()


class SessionManager:

    running = True
    _cache_queue = queue.Queue()
    build_queue = queue.Queue()
    _cache_threads = []

    def __init__(self, graph):
        """
        Start state monitor and caching threads

        :param graph: A DB instance
        """
        # Validate arguments and initialize class
        self.graph = graph
        # State thread monitors the age of sessions and determines whether they need to be rebuilt or logged out
        state_thread = threading.Thread(target=self.state_monitor)
        cache_thread = threading.Thread(target=self.cache_manager)
        state_thread.start()
        cache_thread.start()
        self._cache_threads.append(state_thread)
        self._cache_threads.append(cache_thread)

    def cache_manager(self):
        """
        Thread that reloads the caches for items in the cache queue
         
        """
        while self.running:
            time.sleep(2)
            while self._cache_queue.not_empty:
                session = self._cache_queue.get()
                log.debug("Reloading argument {0} caches for active session {1} owned by user {2}".format(
                   len(session.arguments), session.session_id, session.username
                ))
                # Go through the arguments in the session
                for argument in session.arguments.values():
                    argument.build()

    def state_monitor(self):
        """
        Thread that monitors the state of active sessions, ends expired ones, and puts old active ones in the
        cache queue to be reloaded
        
        """
        while self.running:
            time.sleep(10)
            # Go through all the active sessions
            for session in sessions.sessions:
                try:
                    # Determine how long it's been since the last command was run
                    last_command = session.commands[-1]
                    # If it's been more than 15 minutes since it was run, end the session
                    if last_command.age >= 900:
                        session.logout()
                    # If the session is still valid, check if it's been more than 15 minutes since it was loaded,
                    # and if it is, add it to the reloading queue
                    else:
                        if session.stale:
                            self._cache_queue.put(session)
                except IndexError:
                    # No commands have been run
                    if session.age >= 900:
                        session.logout()

    @property
    def report(self):
        """
        Get the reports for all the sessions
        
        :return session_reports: 
        """
        log.debug("Fetching session reports...")
        time_started = time.time()
        session_reports = []
        command_nums = []
        users = []
        for session in sessions.sessions.values():
            session_reports.append(session.report)
            command_nums.append(len(session.commands))
            session_user = session.username
            if session_user not in users:
                users.append(session_user)

        command_average_num = sum(command_nums)/len(command_nums)
        num_users = len(users)
        num_sessions = len(session_reports)
        time_finished = time.time()
        time_delta = round(time_finished-time_started)
        response = {
            "data":
                {
                    "type": "success",
                    "id": "SESSION_REPORTING_SUCCESSFUL",
                    "text": "{0} users are currently online with a total of {1} active sessions. The sessions have "
                            "an average of {2} commands per session".format(
                                num_users,
                                num_sessions,
                                command_average_num),
                    "reports": session_reports
                },
            "meta":
                {
                    "text": "Reporting action finished in approximately {0} seconds".format(time_delta)
                }
        }
        log.debug("Fetched all session reports in approximately {0} seconds".format(time_delta))
        return response


