"""Real Kujo tool integration with explicitly synthetic proposal data."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from common import ROOT,DEPS,KUJO,read,write,digest,tool,load_operator,verify_package
from factory import initialize
from editorial import perform,DIMENSIONS,record_review

@unittest.skipUnless(KUJO.is_file(),'Run npm run setup for real-tool tests')
class Integration(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()

    def state(self):
        source=write(self.root/'source.txt','This test campaign uses a preserved local source. Setup was observed at five minutes on a busy host. This does not predict performance elsewhere.')
        brief=write(self.root/'brief.json',{'schema':'kujo.publishing-house-factory.brief/v1','title':'Test campaign','audience':'Readers','objective':'Explain the observation','voice':'Clear','constraints':[],'sources':[{'id':'sample','path':'source.txt','url':'https://example.com/fixture'}]})
        with patch('factory.RUNS',self.root/'runs'),patch('factory.run_path',lambda n:self.root/'runs'/n):
            return initialize(brief)

    def test_real_tools_complete_local_package_and_detect_drift(self):
        state=self.state()
        claim={'id':'timing','text':'Setup was observed at five minutes on a busy host.','sourceId':'sample','quote':'Setup was observed at five minutes on a busy host.','qualification':'This does not predict performance elsewhere.'}
        doc={'title':'A bounded observation','blocks':[{'text':claim['text']+' '+claim['qualification'],'claimIds':['timing']}]}
        good={'verdict':'pass','findings':[],'dimensions':{d:'ADEQUATE' for d in DIMENSIONS}}
        def proposal(state,key,role,task,data,schema):
            if key=='commission':return {'angle':'Explain scope','outline':['Observation'],'risks':[]}
            if key=='evidence':return {'claims':[claim],'unknowns':[]}
            if key.startswith('article'):return doc
            if key=='package-review-v1':return {**good,'verdict':'revise','findings':['Clarify the observation.']}
            if key.startswith('review') or key.startswith('package-review'):return good
            if key=='adaptations' or key.startswith('adaptations-revision'):return {'newsletter':doc,'social':[doc,doc,doc],'landing':doc}
            raise AssertionError(key)
        op=load_operator();h=op.House(state,DEPS)
        # Use real phases and canonical records, with synthetic model proposals only.
        for phase in op.PHASES[:7]:
            request={'state_root':str(state),'phase':phase}
            with patch('editorial.propose',side_effect=proposal):
                result=perform(request)
                if phase=='evidence-dossier':
                    self.assertEqual(perform(request),result)
            write(state/'phases'/f'{phase}.json',{'result':result})
        manifest_hash=verify_package(state)
        self.assertTrue((state/'output/adaptations-v1/review.json').exists())
        self.assertTrue((state/'output/adaptations-v2/review.json').exists())
        self.assertEqual(read(state/'output/adaptations-v1/review.json')['verdict'],'revise')
        self.assertEqual(read(state/'output/adaptations-v2/review.json')['verdict'],'pass')
        for name in ['dossier','galleypack','bluepencil','versionseal']:
            self.assertTrue(tool(state,name,'validate')['ok'])
        self.assertTrue((state/'storydesk/records/brief-campaign.json').exists())
        self.assertEqual(read(state/'output/package.json')['status'],'AWAITING_HUMAN_REVIEW')
        # Canonical operator pauses without invoking any publication adapter.
        item=read(state/'items/campaign.json');item['phase_index']=7;item['receipts']=[{'artifact':str(state/'output/package.json'),'sha256':manifest_hash}];write(state/'items/campaign.json',item)
        h.tick(1,False)
        self.assertEqual(read(state/'items/campaign.json')['status'],'approval_required')
        with self.assertRaises(op.OperatorError):h.approve('campaign','0'*64,'test-reviewer')
        with self.assertRaises(ValueError):
            tool(state,'versionseal','approve',{'human_actor':'test-only','package_id':'campaign','package_version':'1','manifest_checksum':'0'*64,'destination':'local-review-only','action':'publish'},record_id='approve-invalid-test',artifact=state/'output/package.json',actor='test-only')
        (state/'output/newsletter.md').write_text('tampered')
        with self.assertRaisesRegex(ValueError,'drift'):verify_package(state)
        (state/'output/adaptations-v2/newsletter.md').write_text('changed versioned artifact')
        with self.assertRaises(ValueError):tool(state,'galleypack','validate')

    def test_lease_and_missing_adapter_fail_closed(self):
        state=self.state();op=load_operator();h=op.House(state,DEPS)
        with h.lease('operator'):
            with self.assertRaises(op.OperatorError):h.tick(1,False)
        with patch.dict('os.environ',{'PUBLISHING_HOUSE_PHASE_ADAPTER':''}):h.tick(1,False)
        self.assertEqual(read(state/'items/campaign.json')['status'],'blocked')
        h.resume('campaign')
        self.assertEqual(read(state/'items/campaign.json')['status'],'in_progress')

    def test_publication_adapter_rejects_effects(self):
        p=subprocess.run([str(ROOT/'bin/phase-adapter')],input=json.dumps({'schema_name':'publishing-house.phase-request','schema_version':'1.0.0','state_root':str(self.root),'phase':'approval-publication'}),text=True,capture_output=True)
        self.assertNotEqual(p.returncode,0)
        self.assertIn('disabled',json.loads(p.stdout)['error'])

    def test_cached_phase_rejects_changed_artifact(self):
        output=write(self.root/'output/article.md','before')
        receipt_file=write(self.root/'phases/primary-piece.json',{'outputs':[{'path':'output/article.md','sha256':digest(output)}]})
        request={'schema_name':'publishing-house.phase-request','schema_version':'1.0.0','state_root':str(self.root),'phase':'asset-production','item':{'id':'campaign','receipts':[{'artifact':str(receipt_file),'sha256':digest(receipt_file)}]}}
        output.write_text('after')
        p=subprocess.run([str(ROOT/'bin/phase-adapter')],input=json.dumps(request),text=True,capture_output=True)
        self.assertNotEqual(p.returncode,0)
        self.assertIn('Prior output changed',json.loads(p.stdout)['error'])

    def test_review_cannot_pass_with_blocking_findings(self):
        review={'verdict':'pass','findings':['Unsupported universal claim'],'dimensions':{d:'ADEQUATE' for d in DIMENSIONS}}
        with self.assertRaises(ValueError):record_review(self.root,'bad-review',review,self.root/'missing')

if __name__=='__main__':unittest.main()
