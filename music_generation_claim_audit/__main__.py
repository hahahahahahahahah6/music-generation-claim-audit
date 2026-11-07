"""Command line interface."""
import argparse
import json
import sys
from . import __version__
from .audit import audit_repo

class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(1, 'error: ' + message + '\n')

def main(argv=None):
    parser = Parser(description='Audit documentation against static Python evidence.')
    parser.add_argument('--version', action='version', version=__version__)
    sub = parser.add_subparsers(dest='command', required=True, parser_class=Parser)
    audit = sub.add_parser('audit')
    audit.add_argument('repo', nargs='?', default='.')
    audit.add_argument('--json', action='store_true')
    audit.add_argument('--verbose', action='store_true')
    audit.add_argument('--ignore', action='append', default=[])
    audit.add_argument('--fail-on', choices=('high', 'medium'), default='high')
    args = parser.parse_args(argv)
    try:
        logger = (lambda message: print(message, file=sys.stderr)) if args.verbose else None
        if logger: logger('Scope: README.md, docs/**/*.md, tests/ fixtures and Python sources in ' + args.repo)
        findings = audit_repo(args.repo, args.ignore, logger)
    except (OSError, UnicodeError) as exc:
        print('error: ' + str(exc), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(findings, indent=2))
    elif findings:
        for finding in findings:
            print('{severity} {rule} {path}: {message}'.format(**finding))
    else:
        print('PASS: no contradictory claims found')
    return 2 if any(f['severity'] == 'HIGH' or args.fail_on == 'medium' for f in findings) else 0

if __name__ == '__main__':
    sys.exit(main())
