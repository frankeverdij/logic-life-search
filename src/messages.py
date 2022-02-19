import re
import src.defaults


def format_carriage_returns(input_string):
    # Convert any newline format (\r, \n, \n\r, \r\n) to just \n
    if '\r' in input_string and '\n' not in input_string:
        return re.sub('\r', '\n', input_string)
    else:
        return re.sub('\r', '', input_string)


def print_message(message, needed_verbosity=2, indent=0):
    """Prints an output message (with the specified indent) if the verbosity is sufficiently high"""

    if src.defaults.verbosity >= needed_verbosity:
        # Split on newline, carriage return or both
        lines = format_carriage_returns(message).split('\n')
        for line in lines:
            print(("    " * indent) + line)
