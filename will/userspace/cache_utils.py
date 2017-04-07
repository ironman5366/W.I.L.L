#Builtin imports
import threading
import logging
import time

#External imports
from neo4j.v1.direct import DirectDriver

log = logging.getLogger()

class cache:
    def build_cache(self, user, datastore):
        # Utilities to build caches for various types of
        pass
    def cache_one(self, datastore, cache_interval=1800):
        """
        Reload the cache for any given datastore. By default only reload it if the time since it has been cached is 
        greater than a half hour. If cache_interval is changed in the parameters, or if the datastore itself specifies
        a custom cache_interval, use that instead.
        
        :param datastore: The datastore to cache, matched from the graphed
        :param cache_interval: A custom cache interval, in seconds
        """
        session = self.graph.session()
        current_time = time.time()
        last_cached = datastore["last_cached"]
        cache_delta = current_time-last_cached
        # If the node specifies the correct cache interval
        if "cache_interval" in datastore.keys():
            cache_interval = datastore["cache_interval"]
        if cache_delta >= cache_interval:
            log.debug("Reloading cache of {0} datastore {1}".format(
                datastore["type"], datastore["label"]
            ))
            # If it's a private datastore
            if datastore["type"] == "private":
                # Isolate the relationship between the user and the datastore to check for user specific settings
                paired_user = datastore["username"]
                user_rel = session.run(
                    "MATCH (d {id: {id}}"
                    "MATCH (u:User {username: {username})-[r:CACHE]->(d)"
                    "RETURN (r)",
                    {
                        "id": datastore["id"],
                        "username": paired_user
                    }
                )
                # TODO: allow the relationship to specify properties from other connected nodes
                if user_rel:
                    pass
        session.close()

    def cache_buffer(self, chunk):
        """
        Feed a chunk of datastores into self.cache_one
        
        :param chunk: An array of datastore objects
        """
        for datastore in chunk:
            self.cache_one(datastore)

    def cache_multi(self, datastores):
        """
        Take a list of datastores, and split it into n number of chunks, where n is self.threads. Put the remainder
        into the last chunk. Start a cache_buffer thread for each chunk, and wait for all the threads.to finish
        
        :param datastores: 
        :return: 
        """
        # Use multithreading to call the cache_one function
        datastores = list(datastores)
        datastore_num = len(datastores)
        log.debug("Caching {0} datastores using {1} threads".format(
            datastore_num, self.threads
        ))
        # Split the datastores into chunks, if there's extra put them on the end. Round down.
        chunk_len = int(datastore_num/self.threads)
        chunks = []
        incr = 0
        for thread_num in range(self.threads):
            if thread_num == self.threads-1:
                chunks.append(datastores[incr:])
            else:
                incr_new = incr+chunk_len
                chunks.append(datastores[incr:incr_new])
                incr = incr_new
        log.debug("Made {0} chunks of length {1}, with the remainder of {2} added to the final chunk".format(
            len(chunks), chunk_len, datastore_num, self.threads
        ))
        for chunk in chunks:
            c_thread = threading.Thread(target=self.cache_buffer, args=(chunk))
            self.cache_threads.append(c_thread)
            c_thread.start()
        # Wait for the threads to finish
        [c.join() for c in self.cache_threads]
        self.cache_threads = []

    def __init__(self, plugins, graph, threads):
        """
        Validate that graph and threads are of the correct type, and set them in the class
        :param graph: 
        :param threads: 
        """
        # Validate arguments and intialize class
        assert type(threads) == int
        self.threads = threads
        assert type(graph) == DirectDriver
        self.graph = graph
        assert type(plugins) == dict
        self.plugins = plugins
        self.cache_threads = []