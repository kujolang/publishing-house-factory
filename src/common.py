"""Trusted local I/O and canonical tool boundaries."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / '.runtime'
DEPS = RUNTIME / 'deps'
RUNS = RUNTIME / 'runs'
KUJO = DEPS / 'kujo/target/release/kujo'


def read(p):
    return json.loads(Path(p).read_text())


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write(p, value):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    text = value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=False) + '\n'
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix='.write-')
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(text)
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
    base = Path(base).resolve()
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


def verify_package(state):
    state = Path(state)
    manifest = state / 'output/package.json'
    m = read(manifest)
    if m.get('schema') != 'kujo.publishing-house-factory.package/v1' or not m.get('files'):
        raise ValueError('Invalid package manifest')
    for entry in m['files']:
        p = confined(state, entry['path'])
        if not p.is_file() or digest(p) != entry['sha256']:
            raise ValueError(f'Package drift: {entry["path"]}')
    return digest(manifest)
