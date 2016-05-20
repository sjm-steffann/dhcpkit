import abc
import itertools
from ipaddress import IPv6Network

from cached_property import cached_property


class ConfigElementFactory(metaclass=abc.ABCMeta):
    """
    Base class for factories to create elements from configuration
    """

    def __init__(self, section):
        self._element = None
        self.section = section
        self.validate_config()

    def validate_config(self):
        """
        Validate if the information in the config section is acceptable
        """
        pass

    def __repr__(self) -> str:
        """
        Simple repr implementation to show the corresponding config
        :return: Config representation
        """
        config = ""
        return str(self.section)

    @abc.abstractmethod
    def create(self) -> object:
        """
        Override this method to create the handler.

        :return: The option handler
        """
        return None

    def __call__(self) -> object:
        """
        Create the handler on demand and return it.

        :return: The option handler
        """
        # Create the handler if we haven't done so yet
        if self._element is None:
            self._element = self.create()

        return self._element


class SubnetBase(metaclass=abc.ABCMeta):
    def __init__(self, section):
        # Store the original section
        self.section = section

        # Check for overlap between our prefixes
        for a, b in itertools.combinations(self.prefixes, r=2):
            if a.overlaps(b):
                if a == b:
                    raise ValueError("Prefix {} is defined twice".format(a))
                else:
                    raise ValueError("Prefixes {} and {} overlap".format(a, b))

        # Check the parent-child relationships
        for subnet in self.section.subnets:
            for subnet_prefix in subnet.prefixes:
                found = False
                for prefix in self.prefixes:
                    # Does this subnet fit into one of our prefixes?
                    if subnet_prefix[0] >= prefix[0] and subnet_prefix[-1] <= prefix[-1]:
                        found = True
                        break

                # We don't contain this subnet, abort
                if not found:
                    raise ValueError('Subnet prefix {} is not part of parent subnet prefixes {}'.format(
                        subnet_prefix,
                        ', '.join(map(str, self.prefixes))
                    ))

        # Check for overlap between our subnets
        for s1, s2 in itertools.combinations(self.subnets, r=2):
            for a, b in itertools.product(s1.prefixes, s2.prefixes):
                if a.overlaps(b):
                    if a == b:
                        raise ValueError("Subnet {} is defined twice".format(a))
                    else:
                        raise ValueError("Subnets {} and {} overlap".format(a, b))

    @property
    @abc.abstractmethod
    def prefixes(self):
        """
        Subclasses overwrite this to provide the prefixes for their specific type

        :return: A list of prefixes
        """
        return []

    def __getattr__(self, item):
        """
        If a property doesn't exist try to get it from our saved section

        :param item: Property name
        :return: Its value, if available in the section data
        """
        return getattr(self.section, item)


class Config(SubnetBase):
    @cached_property
    def prefixes(self):
        # This contains everything
        return [IPv6Network('::/0')]


class Subnet(SubnetBase):
    @cached_property
    def prefixes(self):
        # The name is the prefix
        prefix = self.section.getSectionName()

        # Apply the correct datatype
        return [IPv6Network(prefix)]


class SubnetGroup(SubnetBase):
    @property
    def prefixes(self):
        # Use the prefixes multi-key
        return self.section.prefixes
