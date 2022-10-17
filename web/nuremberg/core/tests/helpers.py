from io import StringIO

from django.core.management import call_command


def do_command_call(command_name, *args, **kwargs):
    """Call a management command having control of stderr and stdout."""
    stdout = kwargs.setdefault('stdout', StringIO())
    stderr = kwargs.setdefault('stderr', StringIO())
    result = call_command(command_name, *args, **kwargs)
    return result, stdout, stderr
