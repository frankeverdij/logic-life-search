import subprocess

def test_version():
    completed_process = subprocess.run(['./lls','-V'])
    assert completed_process.returncode == 0
