import re
import copy


def format_carriage_returns(input_string):
    # Convert any newline format (\r, \n, \n\r, \r\n) to just \n
    if '\r' in input_string and '\n' not in input_string:
        return re.sub('\r', '\n', input_string)
    else:
        return re.sub('\r', '', input_string)


def make_grid(default_cell, *dimensions, template=None):
    if template is not None:
        assert not dimensions, 'Two sets of parameters given to make_grid'
        dimensions = []
        while isinstance(template, list):
            dimensions.insert(0,len(template))
            if template:
                template = template[0]
            else:
                break

    grid = default_cell
    for dimension in dimensions:
        grid = [copy.deepcopy(grid) for _ in range(dimension)]
    return grid
