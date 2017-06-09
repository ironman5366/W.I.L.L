# Userspace
The W.I.L.L userspace relies on a number of different caching and build threads to keep all arguments and information
as accurate as possible.

## Threads
- Session Manager
    - Cache thread
        - Slow caching thread that rebuilds stale arguments
        - Runs every 2 seconds
        - Rebuilds all arguments
        - Runs session.reload()
    - Build thread
        - Fast caching thread that builds arguments for new sessions
        - Runs every 0.2 seconds
        - Runs session.build_arguments()
    - State manager
        - Very slow caching thread that monitors the state of sessions
        - Logs out sessions with no activity for more than 15 minutes
        - Adds old but active sessions to the cache thread
        - Relies on session.stale
