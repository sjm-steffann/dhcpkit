from abc import ABC, abstractmethod
from inspect import Parameter
import inspect


class StructuredElement(ABC):
    """
    A StructuredElement is a specific kind of class that represents a protocol message or option. Structured elements
    have the following extra requirements:

    - The constructor parameters and the internal state properties must be identical
      So if an object has a property `timeout` which is an integer then the constructor must accept a named parameter
      called `timeout` which is stored in that property. The constructor must have appropriate default values if
      possible. Empty objects, lists, dictionaries etc are represented by a default value of None.
    - The full internal state of the object must be loadable from a bytes object with the load_from method
    - The full internal state of the object must be storable as a bytes object with the save method
    """

    @classmethod
    @abstractmethod
    def determine_class(cls, buffer: bytes, offset: int=0) -> type:
        pass

    @classmethod
    def parse(cls, buffer: bytes, offset: int=0, length: int=None) -> (int, type):
        """
        Constructor for a new element of which the state is automatically loaded from the given buffer. Both the number
        of bytes used from the buffer and the instantiated element are returned. The class of the returned element may
        be a subclass of the current class if the parser can determine that the data in the buffer contains a subtype.

        :param buffer: The buffer to read data from
        :param offset: The offset in the buffer where to start reading
        :param length: The amount of data we are allowed to read from the buffer
        :return: The number of bytes used from the buffer and the resulting element
        """
        element_class = cls.determine_class(buffer, offset=offset)
        element = element_class()
        length = element.load_from(buffer, offset=offset, length=length)
        return length, element

    @abstractmethod
    def load_from(self, buffer: bytes, offset: int=0, length: int=None) -> int:
        """
        Load the internal state of this object from the given buffer. The buffer may contain more data after the
        structured element is parsed. This data is ignored.

        :param buffer: The buffer to read data from
        :param offset: The offset in the buffer where to start reading
        :param length: The amount of data we are allowed to read from the buffer
        :return: The number of bytes used from the buffer
        """
        return 0

    @abstractmethod
    def save(self) -> bytes:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        return b''

    def __len__(self) -> int:
        """
        Return the length of this element in bytes. This is the exact length that the save() method will produce. It
        can also be used to determine where to continue after parsing this element from a longer buffer.

        This is an inefficient implementation. Subclass are advised to provide a more efficient one.

        :return: The length in octets of the saved representation of this element
        """
        return len(self.save())

    def __eq__(self, other: object) -> bool:
        """
        Compare this object to another object. The result will be True if they are of the same class and if the
        properties have equal values and False otherwise.

        :param other: The other object
        :return: Whether this object is equal to the other one
        """
        # Use strict comparison, one being a subclass of the other is not good enough
        if type(self) is not type(other):
            return NotImplemented

        # Get the signature of the __init__ method to find the properties we need to compare
        # This is why the object properties and __init__ parameters need to match, besides it being good practice for
        # an object that represents a protocol element anyway...
        signature = inspect.signature(self.__init__)

        # Compare the discovered properties
        for parameter in signature.parameters.values():
            # Skip any potential *args and **kwargs in the method signature
            if parameter.kind in (Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD):
                continue

            if getattr(self, parameter.name) != getattr(other, parameter.name):
                return False

        # Amazing, all properties seem equal
        return True

    def __repr__(self):
        # Get the signature of the __init__ method to find the properties we need to compare
        # This is why the object properties and __init__ parameters need to match, besides it being good practice for
        # an object that represents a protocol element anyway...
        signature = inspect.signature(self.__init__)

        # Create a list of string with "parameter=value" for each parameter of __init__
        options_repr = ['{}={}'.format(parameter.name, repr(getattr(self, parameter.name)))
                        for parameter in signature.parameters.values()
                        if parameter.kind not in (Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD)]

        # And construct a constructor call to show
        return '{}({})'.format(self.__class__.__name__, ', '.join(options_repr))
