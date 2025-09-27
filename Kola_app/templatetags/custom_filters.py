from django import template

register = template.Library()

@register.filter
def get_range(value, max_value):
    """
    Creates a range from value to max_value.
    Usage: {{ value|get_range:max_value }}
    """
    value = int(value)
    max_value = int(max_value)
    return range(value, max_value)