verbosity = 2  # 0, 1, 2 or 3
pattern_output_format = "rle"  # "rle" or "csv"
life_encoding_method = 1  # 0, 1 or 2
rulestring = "B3/S23"  # Any valid rulestring
solver = "kissat"  # One of the following solvers
supported_solvers = [
    "kissat",
    "cadical",
    "glucose",
    "glucose-syrup",
    "lingeling",
    "plingeling",
    "treengeling"
]
assert solver in supported_solvers, 'Solver not recognised'
background = "possible_strobing"  # Any file in backgrounds/
