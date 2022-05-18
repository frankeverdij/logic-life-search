import subprocess

def test_unsat():
    completed_process = subprocess.run(['./lls', '-c', '-s', 'p3', 'x1', '-b6'])
    assert completed_process.returncode == 0

def test_sat():
    completed_process = subprocess.run(['./lls', '-s', 'D8', '-s', 'p1', '-p', '-b3', '-n'])
    assert completed_process.returncode == 0
