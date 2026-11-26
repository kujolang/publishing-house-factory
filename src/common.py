"""Trusted local I/O and canonical tool boundaries."""
from contextlib import contextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / '.runtime'
DEPS = RUNTIME / 'deps'
RUNS = RUNTIME / 'runs'
KUJO = DEPS / 'kujo/target/release/kujo'


MAX_ARTIFACT = 64 * 1024 * 1024
MAX_JSON = 8 * 1024 * 1024
MAX_PACKAGE_FILES = 4096
MAX_PACKAGE_BYTES = 256 * 1024 * 1024
PACKAGE_ROOTS = ('input', 'output', 'phases', 'proposals', 'requests')
PACKAGE_EXCLUSIONS = {'output/package.json', 'phases/format-production.json'}


@contextmanager
def open_regular(path, limit=MAX_ARTIFACT):
    path = Path(path)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as handle:
        initial = os.fstat(descriptor)
        if not stat.S_ISREG(initial.st_mode) or initial.st_size > limit:
            raise ValueError('Expected a bounded regular file')
        yield handle, initial.st_size
        def stamp(info):
            return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
        if (stamp(initial) != stamp(os.fstat(descriptor)) or
                stamp(initial) != stamp(path.stat(follow_symlinks=False))):
            raise ValueError('File changed while reading')


def read_bytes(path, limit):
    with open_regular(path, limit) as (handle, size):
        value = handle.read(size + 1)
        if len(value) != size:
            raise ValueError('File size changed while reading')
    return value


def read(path, limit=MAX_JSON):
    return json.loads(read_bytes(path, limit).decode('utf-8'))


def fingerprint(path, limit=MAX_ARTIFACT):
    checksum = hashlib.sha256()
    with open_regular(path, limit) as (handle, size):
        remaining = size
        while remaining:
            chunk = handle.read(min(remaining, 1024*1024))
            if not chunk:
                raise ValueError('File was truncated while reading')
            remaining -= len(chunk)
            checksum.update(chunk)
        if handle.read(1):
            raise ValueError('File grew while reading')
    return checksum.hexdigest(), size


def digest(path):
    return fingerprint(path)[0]


def write(p, value):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, bytes):
        raw = value
    elif isinstance(value, str):
        raw = value.encode('utf-8')
    else:
        raw = (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode('utf-8')
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix='.write-')
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(raw)
        os.replace(tmp, p)
    finally:
        if Path(tmp).exists():
            Path(tmp).unlink()
    return p


def identifier(s):
    if not isinstance(s, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}', s):
        raise ValueError('Invalid identifier')
    return s


def confined(base, relative):
    base = Path(base)
    if base.is_symlink() or not isinstance(relative, str) or not relative or '\\' in relative or '\x00' in relative:
        raise ValueError('Invalid artifact path')
    base = base.resolve()
    p = Path(relative)
    if p.is_absolute() or '..' in p.parts:
        raise ValueError('Path must stay inside its root')
    current = base
    for part in p.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('Symlinks are not accepted')
    p = (base / p).resolve()
    if not p.is_relative_to(base) or p == base:
        raise ValueError('Path must stay inside its root')
    return p


def load_operator():
    spec = importlib.util.spec_from_file_location('canonical_operator', DEPS / 'kujo-workflows/publishing-house-operator/operator.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def tool(state, name, command, payload=None, record_id=None, artifact=None, actor='publishing-factory'):
    """Replay immutable operations only when the exact prior input is unchanged."""
    state = Path(state)
    args = [str(KUJO), 'run', str(DEPS / name / f'{name}.kujo'), '--', *command.split(), '--state', str(state / name), '--json']
    cache = None
    if payload is not None:
        identifier(record_id)
        payload = {'schema_version':'1.0.0', **payload}
        signature = hashlib.sha256(json.dumps({'payload':payload,'command':command,'artifact':str(artifact),'sha256':digest(artifact) if artifact else None,'actor':actor}, sort_keys=True).encode()).hexdigest()
        cache = state / 'tool-receipts' / name / f'{record_id}.json'
        if cache.exists():
            prior = read(cache)
            if prior['input_sha256'] != signature:
                raise ValueError(f'Immutable tool input changed: {name}/{record_id}')
            # Revalidate the real tool record, not only the cache.
            check = subprocess.run(args[:3] + ['--','verify' if name == 'dossier' else 'validate','--state',str(state/name),'--id',record_id,'--json'], capture_output=True, text=True, timeout=60, cwd=DEPS/name)
            if check.returncode:
                raise ValueError('Prior tool record failed validation')
            return prior['response']
        input_path = write(state / 'tool-inputs' / name / f'{record_id}.json', payload)
        args += ['--input',str(input_path),'--id',record_id,'--actor',actor]
        if artifact:
            args += ['--path',str(artifact)]
    p = subprocess.run(args, capture_output=True, text=True, timeout=90, cwd=DEPS/name)
    try:
        response = json.loads(p.stdout)
    except ValueError:
        raise ValueError(f'{name} did not return JSON') from None
    if p.returncode or not response.get('ok'):
        raise ValueError(f'{name}: {response.get("error_code")}: {response.get("error")}')
    if cache:
        write(cache, {'input_sha256':signature,'response':response})
    return response


def package_files(state):
    state = Path(state)
    if state.is_symlink():
        raise ValueError('Expected a plain campaign directory')
    state = state.resolve()
    files = []
    total = 0
    entries = 0

    def scan(root, depth):
        nonlocal entries, total
        if depth > 32:
            raise ValueError('Package exceeds directory depth limit')
        with os.scandir(root) as scan_entries:
            for entry in scan_entries:
                entries += 1
                if entries > MAX_PACKAGE_FILES * 2:
                    raise ValueError('Package exceeds entry limit')
                p = Path(entry.path)
                relative = p.relative_to(state).as_posix()
                if entry.is_symlink():
                    raise ValueError('Package contains a symlink')
                if entry.is_dir(follow_symlinks=False):
                    scan(p, depth + 1)
                elif not entry.is_file(follow_symlinks=False):
                    raise ValueError('Package contains a special file')
                elif relative not in PACKAGE_EXCLUSIONS:
                    if len(files) >= MAX_PACKAGE_FILES:
                        raise ValueError('Package exceeds file count')
                    checksum, size = fingerprint(p, min(MAX_ARTIFACT, MAX_PACKAGE_BYTES - total))
                    total += size
                    files.append({'path':relative,'sha256':checksum,'bytes':size})

    for folder in PACKAGE_ROOTS:
        root = confined(state, folder)
        if root.exists():
            scan(root, 0)
    return sorted(files, key=lambda entry: Path(entry['path']))


def verify_package(state):
    state = Path(state)
    raw = read_bytes(confined(state, 'output/package.json'), MAX_JSON)
    m = json.loads(raw.decode('utf-8'))
    if (not isinstance(m, dict) or m.get('schema') != 'kujo.publishing-house-factory.package/v1' or
            m.get('externalEffect', False) is not False or
            m.get('status', 'AWAITING_HUMAN_REVIEW') != 'AWAITING_HUMAN_REVIEW' or
            not isinstance(m.get('files'), list) or not 1 <= len(m['files']) <= MAX_PACKAGE_FILES):
        raise ValueError('Invalid package manifest')
    actual = {entry['path']:entry for entry in package_files(state)}
    for expected in m['files']:
        if not isinstance(expected, dict) or not isinstance(expected.get('path'), str):
            raise ValueError('Invalid package entry')
        relative = expected['path']
        entry = actual.pop(relative, None)
        if (entry is None or entry['sha256'] != expected.get('sha256') or
                ('bytes' in expected and (type(expected['bytes']) is not int or entry['bytes'] != expected['bytes']))):
            raise ValueError(f'Package drift: {relative}')
    if actual:
        raise ValueError('Package drift: unexpected retained files')
    return hashlib.sha256(raw).hexdigest()
