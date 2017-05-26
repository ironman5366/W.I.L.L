from unittest.mock import *
import unittest

from will.API import v1


def mock_request(auth={}, doc={}, **kwargs):
    """
    Create a mock request object with an appropriate request context

    :param auth: The optional req.context["auth"] object
    :param doc: The optional req.context["doc"] object
    :param kwargs: Any other args that should be submitted inside the request context
    :return base_class: The final request object
    """
    base_class = MagicMock()
    base_class.context = {}
    base_class.context.update({"auth": auth})
    base_class.context.update({"doc": doc})
    base_class.context.update(kwargs)
    return base_class


def mock_session(return_value=None, side_effect=None):
    """
    Reach into the hooks file and change it's `graph.session` class to a mock method that returns what the tests
    need it to return
    :param return_value: 

    """
    v1.graph = MagicMock()
    v1.graph.session = MagicMock
    if side_effect:
        # Give an option to return it with a side ffect instead of a return value
        assert not return_value
        v1.graph.session.run = MagicMock(side_effect=side_effect)
    else:
        v1.graph.session.run = MagicMock(return_value=return_value)