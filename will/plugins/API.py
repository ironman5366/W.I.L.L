import pyplugins as plugins
import will.logger as logger


init = plugins.event(plugins.EVT_INIT)
shutdown = plugins.event(plugins.EVT_EXIT)
subscribe_to_any = plugins.event(plugins.EVT_ANY_INPUT)
subscribe_to = plugins.event
log = logger.log
