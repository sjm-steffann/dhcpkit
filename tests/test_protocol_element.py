"""
Test whether the basic stuff of ProtocolElement works as intended
"""
import unittest

from dhcpkit.protocol_element import ProtocolElement


class DemoElementBase(ProtocolElement):
    """
    A simple element to test with
    """

    @classmethod
    def determine_class(cls, buffer: bytes, offset: int=0) -> type:
        """
        Intentionally left empty. Specific implementations must be tested separately.

        :param buffer: The buffer to read data from
        :param offset: The offset in the buffer where to start reading
        :return: The best known class for this data
        """

    def load_from(self, buffer: bytes, offset: int=0, length: int=None) -> int:
        """
        Intentionally left empty. Specific implementations must be tested separately.

        :param buffer: The buffer to read data from
        :param offset: The offset in the buffer where to start reading
        :param length: The amount of data we are allowed to read from the buffer
        :return: The number of bytes used from the buffer
        """

    def save(self) -> bytes:
        """
        Intentionally left empty. Specific implementations must be tested separately.

        :return: The buffer with the data from this element
        """


class DemoElement(DemoElementBase):
    """
    Sub-element to test with
    """


class OneParameterDemoElement(DemoElementBase):
    """
    Sub-element to test with
    """

    def __init__(self, one: DemoElementBase):
        self.one = one


class TwoParameterDemoElement(DemoElementBase):
    """
    Sub-element to test with
    """

    def __init__(self, one: int, two: DemoElementBase):
        self.one = one
        self.two = two


class ThreeParameterDemoElement(DemoElementBase):
    """
    Sub-element to test with
    """

    def __init__(self, one: int, two: str, three: [DemoElementBase]):
        self.one = one
        self.two = two
        self.three = three or []


class BadDemoElement(DemoElementBase):
    """
    Sub-element to test with
    """


class ContainerElementBase(DemoElementBase):
    """
    A simple element that contains DemoElements
    """

    def __init__(self, elements: [ProtocolElement]):
        self.elements = elements or []

    def validate(self):
        """
        Validate the contents of this element
        """
        self.validate_contains(self.elements)


class AnythingContainerElement(ContainerElementBase):
    """
    Container that may contain as many as it wants
    """


class NothingContainerElement(ContainerElementBase):
    """
    Container that may contain as many as it wants
    """


class MinOneContainerElement(ContainerElementBase):
    """
    Container that must contain at least one sub-element
    """


class MaxOneContainerElement(ContainerElementBase):
    """
    Container that must contain at most one sub-element
    """


class ExactlyOneContainerElement(ContainerElementBase):
    """
    Container that must contain exactly one sub-element
    """


class ExactlyTwoContainerElement(ContainerElementBase):
    """
    Container that must contain exactly two sub-elements
    """


AnythingContainerElement.add_may_contain(DemoElement)
NothingContainerElement.add_may_contain(DemoElement, 0, 0)
MinOneContainerElement.add_may_contain(DemoElement, 1)
MaxOneContainerElement.add_may_contain(DemoElement, 0, 1)
ExactlyOneContainerElement.add_may_contain(DemoElement, 1, 1)
ExactlyTwoContainerElement.add_may_contain(DemoElement, 2, 2)


# noinspection PyMethodMayBeStatic
class ElementOccurrenceTestCase(unittest.TestCase):
    def test_bad(self):
        container = AnythingContainerElement(elements=[BadDemoElement()])
        self.assertRaisesRegex(ValueError, 'cannot contain BadDemoElement', container.validate)

    def test_class_based(self):
        container = AnythingContainerElement(elements=[])
        self.assertTrue(container.may_contain(DemoElement))
        self.assertFalse(container.may_contain(BadDemoElement))

    def test_anything_0(self):
        container = AnythingContainerElement(elements=[])
        container.validate()

    def test_anything_1(self):
        container = AnythingContainerElement(elements=[DemoElement()])
        container.validate()

    def test_anything_2(self):
        container = AnythingContainerElement(elements=[DemoElement(), DemoElement()])
        container.validate()

    def test_nothing_0(self):
        container = NothingContainerElement(elements=[])
        container.validate()

    def test_nothing_1(self):
        container = NothingContainerElement(elements=[DemoElement()])
        self.assertRaisesRegex(ValueError, 'cannot contain DemoElement', container.validate)

    def test_nothing_2(self):
        container = NothingContainerElement(elements=[DemoElement(), DemoElement()])
        self.assertRaisesRegex(ValueError, 'cannot contain DemoElement', container.validate)

    def test_min_one_0(self):
        container = MinOneContainerElement(elements=[])
        self.assertRaisesRegex(ValueError, 'must contain at least 1 DemoElement', container.validate)

    def test_min_one_1(self):
        container = MinOneContainerElement(elements=[DemoElement()])
        container.validate()

    def test_min_one_2(self):
        container = MinOneContainerElement(elements=[DemoElement(), DemoElement()])
        container.validate()

    def test_max_one_0(self):
        container = MaxOneContainerElement(elements=[])
        container.validate()

    def test_max_one_1(self):
        container = MaxOneContainerElement(elements=[DemoElement()])
        container.validate()

    def test_max_one_2(self):
        container = MaxOneContainerElement(elements=[DemoElement(), DemoElement()])
        self.assertRaisesRegex(ValueError, 'may only contain 1 DemoElement', container.validate)

    def test_exactly_one_0(self):
        container = ExactlyOneContainerElement(elements=[])
        self.assertRaisesRegex(ValueError, 'must contain at least 1 DemoElement', container.validate)

    def test_exactly_one_1(self):
        container = ExactlyOneContainerElement(elements=[DemoElement()])
        container.validate()

    def test_exactly_one_2(self):
        container = ExactlyOneContainerElement(elements=[DemoElement(), DemoElement()])
        self.assertRaisesRegex(ValueError, 'only contain 1', container.validate)

    def test_exactly_two_1(self):
        container = ExactlyTwoContainerElement(elements=[DemoElement()])
        self.assertRaisesRegex(ValueError, 'must contain at least 2 DemoElements', container.validate)

    def test_exactly_two_2(self):
        container = ExactlyTwoContainerElement(elements=[DemoElement(), DemoElement()])
        container.validate()

    def test_exactly_two_3(self):
        container = ExactlyTwoContainerElement(elements=[DemoElement(), DemoElement(), DemoElement()])
        self.assertRaisesRegex(ValueError, 'may only contain 2 DemoElements', container.validate)

    def test_compare(self):
        container1 = AnythingContainerElement(elements=[DemoElement(), DemoElement()])
        container2 = AnythingContainerElement(elements=[DemoElement(), DemoElement()])
        container3 = AnythingContainerElement(elements=[DemoElement(), BadDemoElement()])

        self.assertEqual(container1, container2)
        self.assertNotEqual(container1, container3)

    def test_repr(self):
        element = TwoParameterDemoElement(1608, DemoElement())
        self.assertEqual(repr(element), "TwoParameterDemoElement(one=1608, two=DemoElement())")

    def test_str_no_parameters(self):
        element = DemoElement()
        self.assertEqual(str(element), "DemoElement()")

    def test_str_one_parameter(self):
        element = OneParameterDemoElement(DemoElement())
        self.assertEqual(str(element), "OneParameterDemoElement(one=DemoElement())")

        element = OneParameterDemoElement(one=DemoElement())
        self.assertEqual(str(element), "OneParameterDemoElement(one=DemoElement())")

        element = OneParameterDemoElement(one=TwoParameterDemoElement(1608, DemoElement()))
        self.assertEqual(str(element), "OneParameterDemoElement(\n"
                                       "  one=TwoParameterDemoElement(\n"
                                       "    one=1608,\n"
                                       "    two=DemoElement(),\n"
                                       "  )\n"
                                       ")")

    def test_str_two_parameters(self):
        element = TwoParameterDemoElement(1608, DemoElement())
        self.assertEqual(str(element), "TwoParameterDemoElement(\n"
                                       "  one=1608,\n"
                                       "  two=DemoElement(),\n"
                                       ")")

    def test_str_three_parameters(self):
        element = ThreeParameterDemoElement(1608, 'Something', [
            DemoElement(),
            OneParameterDemoElement(DemoElement()),
            TwoParameterDemoElement(1608, TwoParameterDemoElement(1608, DemoElement()))
        ])
        self.assertEqual(str(element), "ThreeParameterDemoElement(\n"
                                       "  one=1608,\n"
                                       "  two='Something',\n"
                                       "  three=[\n"
                                       "    DemoElement(),\n"
                                       "    OneParameterDemoElement(one=DemoElement()),\n"
                                       "    TwoParameterDemoElement(\n"
                                       "      one=1608,\n"
                                       "      two=TwoParameterDemoElement(\n"
                                       "        one=1608,\n"
                                       "        two=DemoElement(),\n"
                                       "      ),\n"
                                       "    ),\n"
                                       "  ],\n"
                                       ")")


if __name__ == '__main__':
    unittest.main()
