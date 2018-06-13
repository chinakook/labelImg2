# Simple natural order sorting API for Python.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: November 2, 2015
# URL: https://github.com/xolox/python-naturalsort

"""Simple natural order sorting API for Python."""

# Standard library modules.
import re

__version__ = '1.5.1'
"""Semi-standard module versioning."""

integer_pattern = re.compile('([0-9]+)')
"""Compiled regular expression to match a consecutive run of digits."""

integer_type = int
"""The type used to coerce strings of digits into Python numbers."""


def natsort(l, key=None, reverse=False):
    """
    Sort the given list in the way that humans expect (using natural order sorting).

    :param l: An iterable of strings to sort.
    :param key: An optional sort key similar to the one accepted by Python's
                built in :func:`sorted()` function. Expected to produce
                strings.
    :param reverse: Whether to reverse the resulting sorted list.
    :returns: A sorted list of strings.
    """
    return sorted(l, key=lambda v: NaturalOrderKey(key and key(v) or v), reverse=reverse)


def natsort_key(s):
    """
    Turn a string into a list of substrings and numbers.

    :param s: The string to split.
    :returns: A list of strings and/or integers.
    """
    return [coerce(c) for c in integer_pattern.split(s) if c != '']


def coerce(s):
    """
    Coerce strings of digits into proper integers.

    :param s: A string.
    :returns: An integer (if coercion is possible) or the original string.
    """
    if s.isdigit():
        return integer_type(s)
    else:
        return s


class NaturalOrderKey(object):

    """
    Rich comparison for natural order sorting keys.

    This class implements rich comparison operators for natural order sorting
    that is compatible with both Python 2 and Python 3.

    Previous versions of the `naturalsort` package directly compared the
    iterables produced by :func:`natsort_key()` however in Python 3 this can
    raise :exc:`~exceptions.TypeError` due to comparisons between integers and
    strings (which Python 3 does not allow).
    """

    def __init__(self, value):
        """
        Initialize a :class:`NaturalOrderKey` object.

        :param value: A string given to :func:`natsort_key()` to get the
                      natural order sorting key used in the rich comparison
                      methods implemented by this class.
        """
        self.key = natsort_key(value)
        self.length = len(self.key)

    def __eq__(self, other):
        """Equality comparison for natural order sorting keys."""
        if self.is_compatible(other):
            return self.key == other.key
        else:
            return NotImplemented

    def __ne__(self, other):
        """Non equality comparison for natural order sorting keys."""
        if self.is_compatible(other):
            return self.key != other.key
        else:
            return NotImplemented

    def __lt__(self, other):
        """Less than comparison for natural order sorting keys."""
        if self.is_compatible(other):
            for i in range(max(self.length, other.length)):
                if self.length > i:
                    self_item = self.key[i]
                else:
                    self_item = None
                if other.length > i:
                    other_item = other.key[i]
                else:
                    other_item = None
                # If the natural order keys are not of equal length one of the
                # items may be unavailable (None) so we have to compensate:
                #
                #  - If the available item is a number then the unavailable
                #    item is treated as the number zero. This implements zero
                #    padding semantics which ensures that e.g. 0.15 sorts
                #    before 0.15.1.
                #
                # - If the available item is not a number then the two items
                #   are treated as being equal, otherwise the second dot in
                #   '0.15.1' (to continue the example from above) would sort
                #   before the zero padding in the tokenized version of '0.15'
                #   which would then be [0, '.', 15, 0, 0].
                if self_item is None:
                    if isinstance(other_item, integer_type):
                        self_item = 0
                    else:
                        self_item = other_item
                if other_item is None:
                    if isinstance(self_item, integer_type):
                        other_item = 0
                    else:
                        other_item = self_item
                if self_item != other_item:
                    if not isinstance(self_item, integer_type) or not isinstance(other_item, integer_type):
                        # Comparisons between two integers are safe but
                        # otherwise we fall back to a string comparison
                        # to avoid type errors raised by Python 3.
                        self_item = str(self_item)
                        other_item = str(other_item)
                    if self_item < other_item:
                        return True
                    if self_item > other_item:
                        return False
            return False
        else:
            return NotImplemented

    def __le__(self, other):
        """Less than or equal comparison for natural order sorting keys."""
        if self.is_compatible(other):
            return self < other or self == other
        else:
            return NotImplemented

    def __gt__(self, other):
        """Greater than comparison for natural order sorting keys."""
        if self.is_compatible(other):
            return not (self <= other)
        else:
            return NotImplemented

    def __ge__(self, other):
        """Greater than or equal comparison for natural order sorting keys."""
        if self.is_compatible(other):
            return self > other or self == other
        else:
            return NotImplemented

    def is_compatible(self, obj):
        """
        Check if the given object has a compatible type.

        :param obj: The object to check.
        :returns: :data:`True` if the given object is an instance of
                  :class:`NaturalOrderKey`, :data:`False` otherwise.
        """
        return isinstance(obj, self.__class__)
