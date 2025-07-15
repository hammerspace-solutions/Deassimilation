import socket
import ipaddress
from typing import Union

def is_local_machine(target: Union[str, ipaddress.IPv4Address, ipaddress.IPv6Address]) -> bool:
    try:
        # Convert string to IP address if necessary
        if isinstance(target, str):
            try:
                target = ipaddress.ip_address(target)
            except ValueError:
                # If not an IP address, try to resolve hostname
                target = ipaddress.ip_address(socket.gethostbyname(target))
        
        return (
            target.is_private or
            target.is_loopback or
            target.is_link_local or
            str(target).startswith('127.') or
            str(target) == '::1'
        )
    except Exception as e:
        print(f"Error checking if machine is local: {e}")
        return False

# Example usage
test_cases = [
    "localhost",
    "127.0.0.1",
    "192.168.1.1",
    "10.0.0.1",
    "172.16.0.1",
    "www.hammerspace.com",
    "8.8.8.8",  # Google DNS (not local)
]

for case in test_cases:
    result = is_local_machine(case)
    print(f"{case}: {'Local' if result else 'Not local'}")
