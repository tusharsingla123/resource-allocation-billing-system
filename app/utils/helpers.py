"""Helper utility functions"""

def format_date(value):
    """Format date for template display"""
    if value is None:
        return ''
    return value.strftime('%d-%m-%Y')

def currency_format(value):
    """Format currency for template display (no decimals)"""
    return "₹ {:,.0f}".format(value)

def currency_format_new(value):
    """Format currency with 2 decimal places for template display"""
    return "₹ {:,.2f}".format(value)
