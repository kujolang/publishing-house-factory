#!/usr/bin/env python3
"""User-facing commands around the pinned canonical Publishing House Operator."""
import argparse
import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid
from urllib.parse import urlsplit, unquote
sys.dont_write_bytecode = True
from common import ROOT, DEPS, RUNTIME, RUNS, KUJO, read, write, digest, confined, identifier, load_operator, tool, verify_package


def now():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')


def validate_brief(p):
    p=Path(p).resolve()
    if p.stat().st_size>64000:
        raise ValueError('Brief exceeds 64 KB')
    b=read(p)
    required={'schema','title','audience','objective','voice','sources','constraints'}
    if set(b)!=required or b['schema']!='kujo.publishing-house-factory.brief/v1':
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
        if set(s)!={'id','path','url'}:
            raise ValueError('Each source needs id, path, url')
        identifier(s['id'])
        if s['id'] in seen:
            raise ValueError('Duplicate source id')
        seen.add(s['id'])
        url=urlsplit(s['url'])
        if url.scheme!='https' or not url.hostname or url.username or url.password:
            raise ValueError('Use public HTTPS source provenance URLs without credentials')
        source=confined(p.parent,s['path'])
        if not source.is_file() or source.stat().st_size>100000:
            raise ValueError('Sources must be regular UTF-8 files under 100 KB')
        text=source.read_bytes().decode('utf-8')
        if not text.strip() or '\x00' in text:
            raise ValueError('Source text is empty or binary')
        sources.append({**s,'text':text,'sha256':digest(source),'capturedAt':now(),'preservedPath':f'input/sources/{s["id"]}.txt'})
    return b,sources


def doctor():
    checks=[]
    lock=read(ROOT/'sources.lock.json')
    for name,s in lock['repositories'].items():
        p=DEPS/name
        try:
            head=subprocess.check_output(['git','-C',str(p),'rev-parse','HEAD'],text=True,stderr=subprocess.DEVNULL).strip()
            dirty=subprocess.check_output(['git','-C',str(p),'status','--porcelain','--untracked-files=all'],text=True).strip()
            ok=head==s['commit'] and not dirty
        except (OSError,subprocess.CalledProcessError): ok=False
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
    write(state/'input/brief.json',brief)
    write(state/'input/sources.json',sources)
    for s in sources: write(state/s['preservedPath'],s['text'])
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
    write(state/'factory.json',{'schema':'kujo.publishing-house-factory.run/v1','startedAt':now(),'mode':'live','sourcesLockSha256':digest(ROOT/'sources.lock.json'),'publicationEnabled':False})
    return state


def advance(state):
    h=load_operator().House(state,DEPS)
    os.environ['PUBLISHING_HOUSE_PHASE_ADAPTER']=str(ROOT/'bin/phase-adapter')
    os.environ['PYTHONDONTWRITEBYTECODE']='1'
    started=time.monotonic()
    # At most nine phase attempts per invocation; canonical operator owns retries.
    for _ in range(9):
        item=read(state/'items/campaign.json')
        if item['status'] in ['approval_required','blocked','completed']:
            break
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


def status():
    return [{'run':p.name,'title':read(p/'input/brief.json')['title'],'item':read(p/'items/campaign.json'),'summary':read(p/'summary.json') if (p/'summary.json').exists() else None} for p in sorted(RUNS.glob('*'),reverse=True) if (p/'items/campaign.json').exists()][:100]


def serve(port):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.headers.get('Host') not in [f'127.0.0.1:{port}',f'localhost:{port}']:
                self.send_error(403);return
            route=unquote(urlsplit(self.path).path)
            try:
                mime='application/json'; disposition=None
                if route=='/':
                    body=(ROOT/'web/index.html').read_bytes();mime='text/html'
                elif route=='/api/runs': body=json.dumps(status()).encode()
                elif route.startswith('/artifact/'):
                    parts=route.split('/')
                    state=run_path(parts[2]);relative='/'.join(parts[3:])
                    if not relative.startswith(('output/','phases/','proposals/','input/')):
                        raise ValueError('Not an exposed artifact')
                    p=confined(state,relative)
                    if p.stat().st_size>2000000: raise ValueError('Artifact too large')
                    body=p.read_bytes()
                    mime='text/html' if p.suffix=='.html' else 'text/plain; charset=utf-8'
                else: self.send_error(404);return
                self.send_response(200)
                self.send_header('Content-Type',mime)
                self.send_header('Cache-Control','no-store')
                self.send_header('X-Content-Type-Options','nosniff')
                self.send_header('Content-Security-Policy',"default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
                self.end_headers();self.wfile.write(body)
            except (ValueError,OSError,KeyError): self.send_error(404)
        def log_message(self,*args): pass
    print(f'Factory Floor: http://127.0.0.1:{port}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()


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
            h=load_operator().House(state,DEPS)
            if read(state/'items/campaign.json')['status']=='blocked': h.resume('campaign')
        result=advance(state)
    print(json.dumps(result,indent=2))
    return 1 if isinstance(result,dict) and result.get('status') in ['blocked','retry_pending'] else 0


if __name__=='__main__':
    try: sys.exit(main())
    except Exception as e:
        print(json.dumps({'ok':False,'error':str(e)}),file=sys.stderr);sys.exit(1)
