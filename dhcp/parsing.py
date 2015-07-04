from abc import ABC, abstractmethod
from inspect import Parameter
import inspect
import collections

infinite = 2 ** 31 - 1


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

    # Class local property that keeps track of what this class may contain as sub-elements
    _may_contain = set()
    _must_contain_min = dict()
    _may_contain_max = dict()
    _may_contain_anything = False
    _may_contain_from_superclass = True

    def validate(self):
        pass

    def validate_contains(self, elements):
        occurence_counters = collections.Counter()
        min_occurences = dict()
        max_occurences = dict()
        for element in elements:
            # Check if this element may be contained in this one
            element_class, min_occurence, max_occurence = self.get_occurence_data(element)
            if max_occurence < 1:
                raise ValueError("{} can not contain {}".format(self.__class__.__name__, element.__class__.__name__))

            # Count its occurence
            occurence_counters[element_class] += 1
            min_occurences[element_class] = min_occurence
            max_occurences[element_class] = max_occurence

        # Check max occurence
        for element_class, count in occurence_counters.items():
            min_occurence = min_occurences[element_class]
            max_occurence = max_occurences[element_class]
            if count > max_occurence:
                if max_occurence == 1:
                    raise ValueError("{} may only contain 1 {}".format(self.__class__.__name__, element_class.__name__))
                else:
                    raise ValueError("{} may only contain {} {}s".format(self.__class__.__name__, max_occurence,
                                                                         element_class.__name__))
            elif count < min_occurence:
                if min_occurence == 1:
                    raise ValueError("{} must contain at least 1 {}".format(self.__class__.__name__,
                                                                            element_class.__name__))
                else:
                    raise ValueError("{} must contain at least {} {}s".format(self.__class__.__name__, max_occurence,
                                                                              element_class.__name__))

    @classmethod
    @abstractmethod
    def determine_class(cls, buffer: bytes, offset: int=0) -> type:
        """
        Return the appropriate class to parse this element with.

        :param buffer: The buffer to read data from
        :param offset: The offset in the buffer where to start reading
        :return: The best known class for this data
        """
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

    @classmethod
    def clear_may_contain(cls, stop_inheritance=False):
        cls._may_contain = set()
        cls._must_contain_min = dict()
        cls._may_contain_max = dict()
        if stop_inheritance:
            cls._may_contain_from_superclass = False

    @classmethod
    def add_may_contain(cls, klass: type, min_occurence: int=0, max_occurence: int=infinite):
        # Make sure we have our own dictionary so we don't accidentally add to our parent's
        if '_may_contain' not in cls.__dict__:
            cls.clear_may_contain()

        # Add it
        cls._may_contain.add(klass)
        cls._must_contain_min[klass] = min_occurence
        cls._may_contain_max[klass] = max_occurence

    @classmethod
    def get_occurence_data(cls, element: object) -> (type, int, int):
        """
        Get information on how often the given element may/must occur as a sub-element of this one.

        :param element: The element to check
        :return: The class the element is classified as, the minimum occurence and the maximum occurence
        """
        if cls._may_contain_anything:
            return object, 0, infinite

        if '_may_contain' in cls.__dict__:
            # This class has its own list of what it may contain: check it
            for klass in cls._may_contain:
                if isinstance(element, klass):
                    return (klass,
                            cls._must_contain_min.get(klass) or 0,
                            cls._may_contain_max.get(klass) or infinite)

        # Not allowed (yet)
        if cls._may_contain_from_superclass:
            try:
                # Try to see if our superclass can tell us what it may contain
                return cls.__mro__[1].get_occurence_data(element)
            except (IndexError, AttributeError):
                return object, 0, 0

    @classmethod
    def may_contain(cls, element: object) -> bool:
        return cls.get_occurence_data(element)[2] > 0
