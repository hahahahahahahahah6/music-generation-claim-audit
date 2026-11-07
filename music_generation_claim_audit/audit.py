"""Offline documentation matching and module-local AST evidence detection."""
import ast
import os
from pathlib import Path
from .phrases import MUSICGENERATION, NOMUSICGENERATION, GENERIC_NAMES, DEDICATED_CLASSES


def prose(text):
    result = []
    fenced = False
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith('```'):
            fenced = not fenced
            result.append('\n')
        else:
            result.append('\n' if fenced else line.replace('`', ''))
    return ''.join(result)


def consume(text, phrases):
    hits = []
    for phrase in sorted(phrases, key=len, reverse=True):
        start = text.find(phrase)
        while start >= 0:
            hits.append(phrase)
            text = text[:start] + ' ' * len(phrase) + text[start + len(phrase):]
            start = text.find(phrase)
    return text, hits


def match_claims(text):
    remaining, denials = consume(prose(text).lower(), NOMUSICGENERATION)
    _, claims = consume(remaining, MUSICGENERATION)
    return claims, denials


def has_evidence(source):
    tree = ast.parse(source)
    aliases = {}
    shadowed = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                aliases[a.asname or a.name.split('.')[0]] = a.name if a.asname else a.name.split('.')[0]
        elif isinstance(n, ast.ImportFrom):
            for a in n.names:
                aliases[a.asname or a.name] = (n.module or '') + '.' + a.name

    def resolve(n):
        if isinstance(n, ast.Name):
            if n.id in shadowed:
                return ''
            return aliases.get(n.id, n.id)
        if isinstance(n, ast.Attribute):
            base = resolve(n.value)
            if not base or n.attr in shadowed:
                return ''
            return base + '.' + n.attr
        return ''

    def construction(n):
        if not isinstance(n, ast.Call):
            return None
        name = resolve(n.func)
        if not name:
            return None
        leaf = name.rsplit('.', 1)[-1]
        if name == 'transformers.pipeline':
            model = next((k.value for k in n.keywords if k.arg == 'model'), n.args[1] if len(n.args) > 1 else None)
            if n.args and isinstance(n.args[0], ast.Constant) and n.args[0].value == 'text-to-audio' and isinstance(model, ast.Constant) and isinstance(model.value, str) and 'music' in model.value.lower():
                return 'any'
        if leaf in DEDICATED_CLASSES:
            return 'any'
        if 'audiocraft' in name.split('.')[:-1] or 'audiocraft' in '.'.join(name.split('.')[:-1]):
            return 'any'
        if 'magenta' in '.'.join(name.split('.')[:-1]):
            return 'magenta'
        if leaf in ('Suno', 'SunoApi', 'SunoAPI', 'SunoClient'):
            return 'suno'
        return None

    instances = {}
    assignments = [n for n in ast.walk(tree) if isinstance(n, (ast.Assign, ast.AnnAssign))]
    for _ in range(len(assignments) + 1):
        for n in assignments:
            kind = construction(n.value)
            if isinstance(n.value, ast.Name):
                kind = instances.get(n.value.id)
            targets = n.targets if isinstance(n, ast.Assign) else [n.target]
            if kind:
                for target in targets:
                    if isinstance(target, ast.Name) and target.id not in shadowed:
                        instances[target.id] = kind

    def instance(n):
        if isinstance(n, ast.Name):
            return instances.get(n.id)
        return construction(n)

    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        name = resolve(n.func)
        leaf = n.func.attr if isinstance(n.func, ast.Attribute) else name.rsplit('.', 1)[-1]
        if leaf not in shadowed and leaf in GENERIC_NAMES and (isinstance(n.func, ast.Attribute) or isinstance(n.func, ast.Name) and n.func.id in aliases):
            return True
        kind = instance(n.func)
        if kind == 'any':
            return True
        if isinstance(n.func, ast.Attribute):
            kind = instance(n.func.value)
            if kind == 'any' or kind == 'magenta' and n.func.attr == 'generate' or kind == 'suno' and n.func.attr in ('generate', 'create'):
                return True
    return False


def audit_repo(repo, ignore=(), verbose=None):
    root = Path(repo)
    if not root.is_dir():
        raise OSError('Repository is not a directory: ' + str(root))
    docs = []
    fixtures = []
    evidence = False
    excluded = {'.git', '__pycache__', '.venv', 'venv', 'env', '.env'}
    for directory, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in excluded and not (Path(directory) / d / 'pyvenv.cfg').exists() and not any((Path(directory) / d).relative_to(root).as_posix().startswith(x) for x in ignore))
        for filename in sorted(files):
            path = Path(directory) / filename
            rel = path.relative_to(root).as_posix()
            if any(rel.startswith(x) for x in ignore):
                if verbose: verbose('ignored ' + rel)
                continue
            parts = path.relative_to(root).parts
            isdoc = rel == 'README.md' or parts[0] == 'docs' and path.suffix == '.md'
            istest = 'tests' in parts[:-1] and path.suffix in ('.py', '.md', '.txt')
            if path.suffix == '.py' or isdoc or istest:
                text = path.read_text(encoding='utf-8')
                if verbose: verbose('scanned ' + rel)
                if path.suffix == '.py':
                    try:
                        evidence = has_evidence(text) or evidence
                    except SyntaxError as exc:
                        raise OSError('Cannot parse ' + rel + ': ' + str(exc)) from exc
                if isdoc: docs.append((rel, match_claims(text)))
                elif istest: fixtures.append((rel, match_claims(text)))
    findings = []
    def add(path, severity, rule, phrase):
        findings.append(dict(path=path, severity=severity, rule=rule, phrase=phrase, verdict=severity, message='Documentation contradicts detected source evidence: ' + phrase))
    claims_in_docs = any(matches[0] for _, matches in docs)
    for path, (claims, denials) in docs:
        for phrase in claims if not evidence else []:
            add(path, 'HIGH', 'documented-music-generation-claim-false', phrase)
        for phrase in denials if evidence else []:
            add(path, 'HIGH', 'documented-no-music-generation-claim-false', phrase)
    if not evidence and not claims_in_docs:
        for path, (claims, _) in fixtures:
            for phrase in claims:
                add(path, 'MEDIUM', 'documented-music-generation-claim-false', phrase)
    return findings
