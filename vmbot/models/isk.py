# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function


class ISK(float):
    def __format__(self, format_spec):
        """Format the stored value with commonly used prefixes."""
        val = float(self)

        for unit in ["", 'k', 'm', 'b']:
            if val < 1000:
                return format(val, format_spec) + unit
            val /= 1000

        return format(val, format_spec) + 't'
