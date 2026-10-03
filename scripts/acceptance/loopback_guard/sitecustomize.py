"""Acceptance-only Python socket restriction, enabled through PYTHONPATH.

This deliberately is not an OS firewall: native libraries or other processes
can bypass Python audit hooks. The browser requires its separate request guard.
"""

import ipaddress
import json
import os
import sys
from datetime import datetime, timezone


def _loopback(host):
    if isinstance(host, bytes):
        host = host.decode('ascii', errors='replace')
    if host == 'localhost':
        return True
    try:
        return ipaddress.ip_address(str(host).split('%', 1)[0]).is_loopback
    except ValueError:
        return False


def _record(event, address):
    path = os.environ.get('KAIROPSIS_NETWORK_AUDIT')
    if path:
        with open(path, 'a', encoding='utf-8') as stream:
            stream.write(json.dumps({
                'at': datetime.now(timezone.utc).isoformat(),
                'pid': os.getpid(),
                'event': event,
                'address': str(address),
            }) + '\n')


def _audit(event, args):
    address = None
    if event in {'socket.connect', 'socket.sendto', 'socket.bind'}:
        address = args[1]
        host = address[0] if isinstance(address, tuple) else None
    elif event in {'socket.getaddrinfo', 'socket.gethostbyname', 'socket.gethostbyaddr'}:
        host = args[0]
        address = host
    else:
        return
    if not _loopback(host):
        _record('blocked:' + event, address)
        raise PermissionError(f'Acceptance guard permits loopback only: {event} {address!r}')


sys.addaudithook(_audit)
os.environ['KAIROPSIS_LOOPBACK_GUARD_ACTIVE'] = '1'
_record('guard-installed', None)
