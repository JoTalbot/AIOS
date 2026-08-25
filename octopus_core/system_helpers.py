import os
import json
import hashlib

VERSIONS_FILE = '/var/lib/octopus/skills_versions.json'

def get_skill_version(name):
    """Return the recorded version string for an Octopus skill.

    Args:
        name: Skill name to look up in ``VERSIONS_FILE``.

    Returns:
        The version string, or ``"unknown"`` when the versions file or the
        skill entry is missing.
    """
    if not os.path.exists(VERSIONS_FILE): return "unknown"
    with open(VERSIONS_FILE, 'r') as f:
        return json.load(f).get(name, "unknown")

def sign_command(cmd, key_path='/etc/octopus/id/id_ed25519'):
    """Generate a simulated signature digest for a command string.

    Args:
        cmd: Command text to be signed.
        key_path: Path to the signing key (unused in the simulation).

    Returns:
        Hex digest of the simulated signature.
    """
    # Simple simulated signature
    return hashlib.md5(f'CMD-SIG-{cmd}'.encode()).hexdigest()
