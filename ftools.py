from functools import wraps


def memoize(obj):
    # This is taken from the Python Decorator Library on the official Python
    # wiki.  https://wiki.python.org/moin/PythonDecoratorLibrary#Memoize
    # Unfortunately we're using Python 2.x here and lru_cache isn't available

    cache = obj.cache = {}

    @wraps(obj)
    def memoizer(*args, **kwargs):
        key = str(args) + str(kwargs)
        if key not in cache:
            cache[key] = obj(*args, **kwargs)
        return cache[key]
    return memoizer
