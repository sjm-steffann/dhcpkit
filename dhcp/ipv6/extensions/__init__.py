import importlib
import pkgutil


def load_all():
    """
    Load all extensions
    """
    for module_finder, name, ispkg in pkgutil.iter_modules(__path__):
        # Make sure we import all extensions we know about
        importlib.import_module('{}.{}'.format(__name__, name))
