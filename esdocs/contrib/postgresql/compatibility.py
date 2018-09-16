try:
    from psycopg2.extras import Range
except ImportError:
    Range = None


def range_field(value):
    if Range and isinstance(value, Range):
        if value.isempty:
            return {}
        upper_type = 'lte' if value.upper_inc else 'lt'
        lower_type = 'gte' if value.lower_inc else 'gt'
        return {
            upper_type: value.upper,
            lower_type: value.lower
        }
    return value


__all__ = [range_field]
