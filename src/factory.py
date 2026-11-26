#!/usr/bin/env python3
"""User-facing commands around the pinned canonical Publishing House Operator."""
import argparse
from contextlib import contextmanager
import datetime
import heapq
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import fcntl
import hashlib
import os
from pathlib import Path
import stat
import subprocess
import shutil
import sys
import time
import uuid
import re
from threading import BoundedSemaphore
from urllib.parse import urlsplit, unquote
sys.dont_write_bytecode = True
from common import ROOT, DEPS, RUNTIME, RUNS, KUJO, read, read_bytes, write, digest, confined, identifier, load_operator, tool, verify_package


def now():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')


def validate_brief(p):
    p=Path(p).absolute()
    p=confined(p.parent,p.name)
    b=read(p,64000)
    required={'schema','title','audience','objective','voice','sources','constraints'}
    if not isinstance(b,dict) or set(b)!=required or b['schema']!='kujo.publishing-house-factory.brief/v1':
        raise ValueError('Use the documented brief schema')
    for k in ['title','audience','objective','voice']:
        if not isinstance(b[k],str) or not b[k].strip() or len(b[k])>8000:
            raise ValueError(f'Invalid {k}')
    if not isinstance(b['constraints'],list) or len(b['constraints'])>20 or any(not isinstance(x,str) or len(x)>2000 for x in b['constraints']):
        raise ValueError('Constraints must be up to 20 short strings')
    if not isinstance(b['sources'],list) or not 1<=len(b['sources'])<=10:
        raise ValueError('Provide 1–10 local text sources')
    seen=set(); sources=[]
    for s in b['sources']:
        if not isinstance(s,dict) or set(s)!={'id','path','url'} or not isinstance(s['url'],str):
            raise ValueError('Each source needs id, path, url')
        identifier(s['id'])
        if s['id'] in seen:
            raise ValueError('Duplicate source id')
        seen.add(s['id'])
        url=urlsplit(s['url'])
        if url.scheme!='https' or not url.hostname or url.username or url.password:
            raise ValueError('Use public HTTPS source provenance URLs without credentials')
        source=confined(p.parent,s['path'])
        try:
            raw=read_bytes(source,100000)
        except (OSError,ValueError) as error:
            raise ValueError('Sources must be regular UTF-8 files under 100 KB') from error
        text=raw.decode('utf-8')
        if not text.strip() or '\x00' in text:
            raise ValueError('Source text is empty or binary')
        sources.append({**s,'text':text,'sha256':hashlib.sha256(raw).hexdigest(),'capturedAt':now(),'preservedPath':f'input/sources/{s["id"]}.txt'})
    return b,sources


def doctor():
    checks=[]
    lock=read(ROOT/'sources.lock.json')
    for name,s in lock['repositories'].items():
        p=DEPS/name
        try:
            if p.is_symlink() or DEPS.is_symlink():
                raise ValueError('Dependency directories must be plain checkouts')
            root=subprocess.check_output(['git','-C',str(p),'rev-parse','--show-toplevel'],text=True,stderr=subprocess.DEVNULL,timeout=30).strip()
            head=subprocess.check_output(['git','-C',str(p),'rev-parse','HEAD'],text=True,stderr=subprocess.DEVNULL,timeout=30).strip()
            dirty=subprocess.check_output(['git','-C',str(p),'status','--porcelain','--untracked-files=all'],text=True,timeout=30).strip()
            ok=Path(root).resolve()==p.resolve() and head==s['commit'] and not dirty
        except (OSError,ValueError,subprocess.SubprocessError): ok=False
        checks.append({'name':name,'ok':ok})
    checks.append({'name':'phase-adapter','ok':os.access(ROOT/'bin/phase-adapter',os.X_OK)})
    checks.append({'name':'kujo-runtime','ok':KUJO.is_file()})
    if all(x['ok'] for x in checks):
        for name in ['storydesk','dossier','galleypack','bluepencil','versionseal','presswire']:
            try:
                tool(RUNTIME/'doctor',name,'doctor')
                checks.append({'name':name+'-runtime','ok':True})
            except Exception as e: checks.append({'name':name+'-runtime','ok':False,'error':str(e)})
    return {'ok':all(x['ok'] for x in checks),'checks':checks,'providerLoginConfigured':(RUNTIME/'provider/auth.json').is_file(),'publicationEnabled':False}


def run_path(name):
    return confined(RUNS,identifier(name))


def initialize(brief_path):
    brief,sources=validate_brief(brief_path)
    name=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]
    state=run_path(name)
    state.mkdir(parents=True,mode=0o700)
    try:
        return capture(state,brief,sources)
    except BaseException:
        shutil.rmtree(state)
        raise


def capture(state,brief,sources):
    write(state/'input/brief.json',brief)
    write(state/'input/sources.json',sources)
    for s in sources: write(state/s['preservedPath'],s['text'].encode('utf-8'))
    h=load_operator().House(state,DEPS)
    h.init()
    # A new factory state has exactly one local profile. Canonical defaults refer
    # to their author's deployment repositories and cannot apply to this install.
    for p in (state/'profiles').glob('*.json'): p.unlink()
    profile={'schema_name':'publishing-house.publication-profile','schema_version':'1.0.0','id':'local-campaign','identity':{'name':brief['title']},'publication_type':'local-review-package','canonical_repository':str(ROOT),'source_of_truth':{'content':['output']},'audience':brief['audience'],'editorial_mission':brief['objective'],'voice_profile':'brief.voice','content_formats':['campaign'],'frontmatter':{'format':'none'},'claim_policy':{'material_claims':'source-mapped'},'evidence_policy':{'captured_sources':True},'build':{'renderer':'escaped-html'},'deployment':{'adapter':'disabled'},'verification':{'exact_hashes':True},'approval_policy':{'default':'REQUIRE_EXACT_HUMAN_APPROVAL','automatic_classes':[]},'refresh_policy':{'method':'new-run'},'correction_policy':{'invalidate_on_change':True}}
    profile_path=write(state/'input/profile.json',profile)
    h.add_profile(profile_path)
    for name in ['dossier','galleypack','bluepencil','versionseal','presswire']: tool(state,name,'init')
    h.intake('local-campaign',[str(state/s['preservedPath']) for s in sources],None,'campaign','normal',brief['title'])
    plan=write(state/'input/plan.json',{'schema_name':'publishing-house.editorial-plan','id':'campaign-plan','kind':'campaign','items':[{'id':'campaign','publication':'local-campaign','type':'campaign','title':brief['title'],'source':str(state/'input/brief.json')}]})
    h.import_plan(plan)
    write(state/'factory.json',{'schema':'kujo.publishing-house-factory.run/v1','startedAt':now(),'mode':'live','sourcesLockSha256':digest(ROOT/'sources.lock.json'),'publicationEnabled':False,
        'inputSha256':{
            'brief':digest(state/'input/brief.json'),
            'sources':digest(state/'input/sources.json'),
        }})
    return state


@contextmanager
def runner_lock(state):
    lock=confined(state,'factory-runner.lock')
    fd=os.open(lock,os.O_WRONLY|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,0o600)
    with os.fdopen(fd,'a') as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise ValueError('Expected a regular campaign lock')
        try:
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Another factory runner is active') from None
        yield


@contextmanager
def adapter_environment(state):
    overrides={
        'PUBLISHING_HOUSE_PHASE_ADAPTER':str(ROOT/'bin/phase-adapter'),
        'PUBLISHING_FACTORY_RUN_ROOT':str(state.resolve()),
        'PYTHONDONTWRITEBYTECODE':'1',
    }
    saved={key:os.environ.get(key) for key in overrides}
    os.environ.update(overrides)
    try:
        yield
    finally:
        for key,value in saved.items():
            if value is None:
                os.environ.pop(key,None)
            else:
                os.environ[key]=value


def advance(state, *, resume=False):
    state=Path(state)
    with runner_lock(state):
        item=read(confined(state,'items/campaign.json'))
        if item['status']=='approval_required':
            return {'run':state.name,'status':'approval_required','packageSha256':verify_package(state),
                    'package':'output/package.json','externalEffect':False,'durationThisInvocationSeconds':0}
        marker=read(confined(state,'factory.json'))
        if marker.get('sourcesLockSha256')!=digest(ROOT/'sources.lock.json'):
            raise ValueError('Pinned dependencies changed; start a new campaign')
        h=load_operator().House(state,DEPS)
        if resume and item['status']=='blocked':
            h.resume('campaign')
        with adapter_environment(state):
            return run_phases(state,h)


def run_phases(state,h):
    started=time.monotonic()
    # At most nine phase attempts per invocation; canonical operator owns retries.
    for _ in range(9):
        item=read(state/'items/campaign.json')
        if item['status'] in ['approval_required','blocked','completed']:
            break
        if item['phase_index']>=7 and item.get('approval_reference'):
            raise ValueError('External publication is disabled for this campaign')
        h.tick(1,False)
        item=read(state/'items/campaign.json')
        print(json.dumps({'run':state.name,'phaseIndex':item['phase_index'],'status':item['status']}),flush=True)
        # Canonical tick IDs have one-second resolution; preserve unique receipts.
        time.sleep(1.05)
    item=read(state/'items/campaign.json')
    summary={'run':state.name,'status':item['status'],'durationThisInvocationSeconds':round(time.monotonic()-started,3),'externalEffect':False}
    if item['status']=='approval_required':
        summary['packageSha256']=verify_package(state)
        summary['package']='output/package.json'
    write(state/'summary.json',summary)
    return summary


def status(*, public=False):
    if RUNS.is_symlink() or not RUNS.is_dir():
        return []
    with os.scandir(RUNS) as entries:
        names=heapq.nlargest(100,(entry.name for entry in entries if
            re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}',entry.name) and entry.is_dir(follow_symlinks=False)))
    records=[]
    for name in names:
        try:
            state=run_path(name)
            marker=confined(state,'factory.json')
            if not marker.is_file():
                continue
            item=read(confined(state,'items/campaign.json'))
            title=read(confined(state,'input/brief.json'),128000)['title']
            if not isinstance(title,str) or not isinstance(item.get('status'),str) or type(item.get('phase_index')) is not int:
                continue
            summary_path=confined(state,'summary.json')
            summary=read(summary_path) if summary_path.is_file() else None
            if public:
                view={key:item.get(key) for key in ('status','phase_index','updated_at')}
                if item.get('blocker'):
                    view['blocker']={'message':'Inspect the local campaign for recovery details.'}
                summary=summary.get('packageSha256') if isinstance(summary,dict) else None
                if not isinstance(summary,str) or not re.fullmatch('[a-f0-9]{64}',summary):
                    summary=None
                item=view
            records.append({'run':name,'title':title,'item':item,'summary':summary})
        except (ValueError,OSError,KeyError,TypeError,AttributeError):
            # A corrupt or partial local campaign must not hide other campaigns.
            continue
    return records


PREVIEWS={
    'input/brief.json','input/sources.json',
    'output/article.md','output/article.json','output/newsletter.md','output/social.md',
    'output/landing.html','output/adaptations.json','output/package.json',
    *(f'phases/{name}.json' for name in (
        'commissioning','evidence-dossier','primary-piece','asset-production',
        'editorial-review','adaptation','format-production')),
    *(f'proposals/{key}-v{version}.json' for key in ('review','package-review') for version in range(1,4)),
}
FLOOR_CSP="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
ARTIFACT_CSP="default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'; sandbox"


class FloorServer(ThreadingHTTPServer):
    def __init__(self,address,handler):
        self.slots=BoundedSemaphore(12)
        super().__init__(address,handler)

    def get_request(self):
        connection,address=super().get_request()
        connection.settimeout(8)
        return connection,address

    def process_request(self,connection,address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(connection)
            return
        try:
            super().process_request(connection,address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self,connection,address):
        try:
            super().process_request_thread(connection,address)
        finally:
            self.slots.release()


def serve(port):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            hosts=self.headers.get_all('Host',[])
            if len(hosts)!=1 or hosts[0] not in [f'127.0.0.1:{port}',f'localhost:{port}']:
                self.send_error(403)
                return
            if (self.headers.get('Sec-Fetch-Site')=='cross-site' or
                    self.headers.get('Origin',f'http://{hosts[0]}')!=f'http://{hosts[0]}'):
                self.send_error(403)
                return
            route=unquote(urlsplit(self.path).path)
            try:
                mime='application/json; charset=utf-8'
                csp=ARTIFACT_CSP
                if route=='/':
                    body=read_bytes(ROOT/'web/index.html',2000000)
                    mime='text/html; charset=utf-8'
                    csp=FLOOR_CSP
                elif route=='/api/runs':
                    body=json.dumps(status(public=True)).encode('utf-8')
                elif route.startswith('/artifact/'):
                    _,_,run,relative=route.split('/',3)
                    if relative not in PREVIEWS:
                        self.send_error(404)
                        return
                    p=confined(run_path(run),relative)
                    body=read_bytes(p,8*1024*1024 if p.suffix=='.json' else 2000000)
                    if p.suffix!='.json':
                        mime='text/html; charset=utf-8' if relative=='output/landing.html' else 'text/plain; charset=utf-8'
                else:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header('Content-Type',mime)
                self.send_header('Content-Length',str(len(body)))
                self.send_header('Cache-Control','no-store')
                self.send_header('X-Content-Type-Options','nosniff')
                self.send_header('Cross-Origin-Resource-Policy','same-origin')
                self.send_header('Content-Security-Policy',csp)
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError,ConnectionResetError,TimeoutError):
                self.close_connection=True
            except (ValueError,OSError,KeyError,IndexError):
                self.send_error(404)

        def log_message(self,*args):
            pass

    print(f'Factory Floor: http://127.0.0.1:{port}',flush=True)
    with FloorServer(('127.0.0.1',port),Handler) as server:
        server.serve_forever()


def main():
    parser=argparse.ArgumentParser(description='Sourced briefs to local editorial packages; no external publication.')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('doctor');sub.add_parser('status')
    sub.add_parser('run').add_argument('brief')
    sub.add_parser('resume').add_argument('run')
    sub.add_parser('verify').add_argument('run')
    s=sub.add_parser('serve');s.add_argument('--port',type=int,default=4382)
    a=parser.parse_args()
    if a.command=='doctor':
        result=doctor();print(json.dumps(result,indent=2));return 0 if result['ok'] else 1
    if a.command=='serve': serve(a.port);return 0
    if a.command=='status': result=status()
    elif a.command=='verify':
        state=run_path(a.run)
        checksum=verify_package(state)
        tool(state,'galleypack','validate')
        result={'run':a.run,'packageSha256':checksum,'ok':True}
    else:
        if not doctor()['ok']: raise ValueError('Run npm run setup, then npm run doctor')
        if a.command=='run': state=initialize(a.brief)
        else:
            state=run_path(a.run)
        result=advance(state,resume=a.command=='resume')
    print(json.dumps(result,indent=2))
    return 1 if isinstance(result,dict) and result.get('status') in ['blocked','retry_pending'] else 0


if __name__=='__main__':
    try: sys.exit(main())
    except Exception as e:
        print(json.dumps({'ok':False,'error':str(e)}),file=sys.stderr);sys.exit(1)
