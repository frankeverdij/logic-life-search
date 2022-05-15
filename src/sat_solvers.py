import time
import subprocess
import threading
import os
import errno
import sys
import re
import enum
import src.files
import src.defaults
from src.messages import print_message

class Status(enum.Enum):
    SAT = 'Satisfiable'
    UNSAT = 'Unsatisfiable'
    TIMEOUT = 'Timed out'
    DRYRUN = 'Dry run'
    INTERRUPT = 'Keyboard interrupt'
    ERROR = 'Error'

def sat_solve(search_pattern, solver=None, parameters=None, timeout=None, indent=0):
    """Solve the given DIMACS problem, using the specified SAT solver"""

    print_message('Solving...', indent=indent)

    if solver is None:
        solver = src.defaults.solver

    dimacs_string = search_pattern.clauses.make_string(indent=indent + 1)

    status, solution, time_taken = use_solver(solver, dimacs_string, parameters=parameters, timeout=timeout, indent=indent+1)

    if status == Status.SAT:
        solution = search_pattern.substitute_solution(
            solution,
            indent=indent + 1
        )

    print_message('Done\n', indent=indent)
    return status, solution, time_taken


def use_solver(solver, dimacs_string, parameters=None, timeout=None, indent=0):
    parameter_list = parameters.strip(" ").split(" ") if parameters is not None else[]
    solver_path = sys.path[0] + "/solvers/" + solver
    command = [solver_path] + parameter_list

    solver_process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    def kill(process):
        process.kill()

    timeout_timer = threading.Timer(timeout, kill, [solver_process])

    print_message('Solving with "' + solver + '" ... (Start time: ' + time.ctime() + ")", 3, indent=indent)

    keyboard_interrupt_flag = False
    start_time = time.time()
    timeout_timer.start()
    try:
        out, error = solver_process.communicate(dimacs_string.encode())
    except KeyboardInterrupt:
        solver_process.kill()
        keyboard_interrupt_flag = True
    end_time = time.time()
    timeout_flag = not timeout_timer.is_alive()
    timeout_timer.cancel()
    print_message('Done\n', 3, indent=indent)

    solution = None
    time_taken = end_time - start_time
    print_message('Time taken: ' + str(time_taken), 3, indent=indent)

    if keyboard_interrupt_flag:
        status = Status.INTERRUPT
    elif timeout_flag:
        status = Status.TIMEOUT
    elif error:
        print_message('Error: "' + error.decode("utf-8") + '"', 3, indent=indent)
        status = Status.ERROR
    else:
        out = out.decode("utf-8")
        print_message("SAT solver output:", 3, indent=indent)
        print_message(out, 3, indent=indent + 1)
        print_message('Done\n', 3, indent=indent)
        print_message('Parsing SAT solver output...', 3, indent=indent)
        status, solution = format_dimacs_output(out, indent=indent)
        print_message('Done', 3, indent=indent)

    return status, solution, time_taken


def format_dimacs_output(dimacs_output, indent=0):

    lines = dimacs_output.strip('\n').split('\n')

    statuses = [line[2:] for line in lines if line[0] == 's']
    variable_lines = [line[2:] for line in lines if line[0] == 'v']

    if len(statuses) != 1:
        raise Exception('Wrong number of status lines')
    if statuses[0] == 'UNSATISFIABLE':
        return Status.UNSAT, None
    elif statuses[0] == 'SATISFIABLE':
        solution = set(literal for line in variable_lines for literal in line.split() if literal != '0')
        return Status.SAT, solution
