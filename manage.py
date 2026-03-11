#!/usr/bin/env python
"""JDS Business AI - Django Management Script"""
import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django konnte nicht importiert werden. Stelle sicher, dass Django "
            "installiert ist und die virtuelle Umgebung aktiv ist."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
