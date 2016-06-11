# coding: utf-8

class ISK(float):
    """Represent ISK values."""

    def __format__(self, format_spec):
        """Format the ISK value with commonly used prefixes."""
        for unit in ['', 'k', 'm', 'b']:
            if self < 1000:
                return format(self, format_spec) + unit
            self /= 1000
        return format(self, format_spec) + 't'
