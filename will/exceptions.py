class CredentialsError(Exception):
    pass


class ConfigurationError(Exception):
    pass


class PluginError(Exception):
    pass


class ModuleLoadError(Exception):
    pass


class DBNotInitializedError(Exception):
    pass