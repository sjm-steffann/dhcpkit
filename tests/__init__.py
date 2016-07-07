"""
All the unit tests go here
"""
import copy
from unittest import mock


class DeepCopyMagicMock(mock.MagicMock):
    """
    A magic mock class that deep-copies the method arguments to check the state of mutable objects at call time
    """
    def _mock_call(self, *args, **kwargs):
        return super()._mock_call(*copy.deepcopy(args), **copy.deepcopy(kwargs))
