from abc import ABC, abstractmethod
from inspect import Parameter


class StructuredElement(ABC):
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

    def __repr__(self):
        # Use introspection to find the parameters to the __init__ method
        import inspect

        signature = inspect.signature(self.__init__)

        # Create a list of string with "parameter=value" for each parameter of __init__
        options_repr = ['{}={}'.format(parameter, repr(getattr(self, parameter)))
                        for parameter in signature.parameters.values()
                        if parameter.kind not in (Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD)]

        # And construct a constructor call to show
        return '{}({})'.format(self.__class__.__name__, ', '.join(options_repr))
