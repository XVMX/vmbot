# coding: utf-8


class ISK(float):
    """Represent ISK values."""

    def __format__(self, format_spec):
        """Format the stored value with commonly used prefixes."""
        val = float(self)

        for unit in ["", 'k', 'm', 'b']:
            if val < 1000:
                return format(val, format_spec) + unit
            val /= 1000

        return format(val, format_spec) + 't'
