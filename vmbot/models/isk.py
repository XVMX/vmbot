# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function


class ISK(float):
    """Store and properly format an ISK value."""

    def __format__(self, format_spec):
        """Format the stored value with commonly used suffixes."""
        val = float(self)

        for unit in ["", 'k', 'm', 'b']:
            if abs(val) < 1000:
                return format(val, format_spec) + unit
            val /= 1000

        return format(val, format_spec) + 't'
