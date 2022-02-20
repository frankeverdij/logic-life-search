import src.defaults
from src.utilities import format_carriage_returns

def print_message(message, needed_verbosity=2, indent=0):
    """Prints an output message (with the specified indent) if the verbosity is sufficiently high"""

    if src.defaults.verbosity >= needed_verbosity:
        # Split on newline, carriage return or both
        lines = format_carriage_returns(message).split('\n')
        for line in lines:
            print(("    " * indent) + line)
