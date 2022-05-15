import time
import subprocess
import threading
import os
import errno
import sys
import re
import src.files
import src.defaults
from src.messages import print_message


def sat_solve(search_pattern, solver=None, parameters=None, timeout=None, save_dimacs=None, dry_run=None, indent=0):
    """Solve the given DIMACS problem, using the specified SAT solver"""

    print_message('Solving...', indent=indent)
    indent += 1
    print_message('Preparing SAT solver input...', 3, indent=indent)

    if solver is None:
        solver = src.defaults.solver

    if solver not in src.defaults.supported_solvers:
        raise ValueError

    if save_dimacs is None:
        file_number = 0
        while True:
            dimacs_file = "lls_dimacs" + str(file_number) + ".cnf"
            file_number += 1
            if not os.path.isfile(dimacs_file):
                break
    else:
        dimacs_file = save_dimacs

    # The solvers prefer their input as a file, so write it out
    search_pattern.clauses.make_file(dimacs_file, indent=indent + 1)

    print_message('Done\n', 3, indent=indent)
    if not dry_run:
        solution, time_taken = use_solver(solver, dimacs_file, parameters=parameters, timeout=timeout, indent=indent)
    else:
        solution = "DRYRUN\n"
        time_taken = None

    if save_dimacs is None:
        print_message('Removing DIMACS file...', 3, indent=indent)
        try:
            os.remove(dimacs_file)
        except OSError as e:
            if e.errno == errno.ENOENT:
                print_message('DIMACS file "' + dimacs_file + '" not found', 3, indent=indent + 1)
            else:
                raise
        print_message('Done\n', 3, indent=indent)
    indent -= 1
    if solution not in ["UNSAT\n", "TIMEOUT\n", "DRYRUN\n"]:
        sat = "SAT"
        solution = search_pattern.substitute_solution(
            solution,
            indent=indent + 1
        )
    else:
        sat = solution[:-1]
        solution = None
    print_message('Done\n', indent=indent)
    return solution, sat, time_taken


def use_solver(solver, file_name, parameters=None, timeout=None, indent=0):
    if parameters is not None:
        parameter_list = parameters.strip(" ").split(" ")
    else:
        parameter_list = []

    solver_path = sys.path[0] + "/solvers/" + solver

    if solver in ["MapleCOMSPS", "MapleCOMSPS_LRB", "riss"]:
        command = [solver_path, file_name, "temp_SAT_solver_output"] + parameter_list
    elif solver in ["lingeling", "plingeling", "treengeling", "cadical", "kissat"]:
        command = [solver_path, file_name] + parameter_list
    elif solver in ["glucose", "glucose-syrup"]:
        command = [solver_path, file_name, "-model"] + parameter_list
    else:
        assert False, "Solver not recognised"

    solver_process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    timeout_flag = [False]  # We want the flag to be mutable, so we put it into a little box.

    def timeout_function(process, flag):
        process.kill()
        flag[0] = "TIMEOUT"

    timeout_timer = threading.Timer(timeout, timeout_function, [solver_process, timeout_flag])

    print_message('Solving with "' + solver + '" ... (Start time: ' + time.ctime() + ")", 3, indent=indent)

    start_time = time.time()
    try:
        timeout_timer.start()
        out, error = solver_process.communicate()
    except KeyboardInterrupt:
        solver_process.kill()
        timeout_flag[0] = "SIGINT"
    finally:
        out = out.decode("utf-8")
        error = error.decode("utf-8")
        timeout_timer.cancel()
        time_taken = time.time() - start_time

    if not timeout_flag[0]:
        print_message('Done\n', 3, indent=indent)

        print_message('Formatting SAT solver output...', 3, indent=indent)

        if solver in ["MapleCOMSPS", "MapleCOMSPS_LRB", "riss"]:
            solution = src.files.string_from_file("temp_SAT_solver_output", indent=indent + 1)
            print_message('Removing SAT solver output file...', 3, indent=indent + 1)
            os.remove("temp_SAT_solver_output")
            print_message('Done\n', 3, indent=indent + 1)
        elif solver in ["lingeling", "plingeling", "treengeling", "cadical", "kissat"]:
            solution = str(out)
            solution = solution.split("\ns ")
            solution = solution[1]
            solution = solution.split("\nc")
            solution = solution[0]
            solution = solution.split("\nv ")
            solution = solution[0] + "\n" + " ".join(solution[1:])
        elif solver in ["glucose", "glucose-syrup"]:
            try:
                solution = out.split("\ns ")[1]
                solution = re.sub("s ", "", solution)
                solution = re.sub("v ", "", solution)
            except IndexError:
                solution = "UNSAT\n"

        if solver == "MapleCOMSPS_LRB":
            if solution == "":
                solution = "UNSAT\n"
        if solver == "riss":
            solution = re.sub("s ", "", solution)
            solution = re.sub("v ", "", solution)
        if "UNSAT" in solution.upper():
            solution = "UNSAT\n"

        print_message("SAT solver output:", 3, indent=indent + 1)
        print_message(out, 3, indent=indent + 2)
        print_message('Error (if any): "' + error + '"', 3, indent=indent + 1)
        print_message('Time taken: ' + str(time_taken), 3, indent=indent + 1)
        print_message('Done\n', 3, indent=indent)

    else:
        print_message('Timed out\n', 3, indent=indent)
        solution = "TIMEOUT\n"

    return solution, time_taken
