from fabric import Connection

from . import PythonInstance

def get_python_instances(conn: Connection, verbose: bool = True) -> list[PythonInstance]:
    cmd = "ls /usr/bin/python3.*"
    result = conn.run(cmd, hide=True)
    instances = []

    if verbose: print("Searching for Python instances...")
    for line in result.stdout.splitlines():
        version = line.split("/")[-1].replace("python", "")
        instances.append(PythonInstance(version=version, executable=line.strip()))
        if verbose: print(f"Found Python {version} at {line.strip()}")

    if not instances: raise RuntimeError("No Python instances found on the remote host.")
    
    return instances

def get_target_python_instance(connection: Connection, target_version: str, verbose: bool = True) -> PythonInstance:
    python_instances = get_python_instances(connection, verbose=verbose)
    if verbose: print(f"Checking for Python version {target_version}...")
    for instance in python_instances:
        if instance.version.startswith(target_version):
            if verbose: print(f"Selected Python {instance.version} at {instance.executable}")
            return instance
    raise RuntimeError(f"No Python instance found for version {target_version}")