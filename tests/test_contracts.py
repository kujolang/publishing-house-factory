import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from common import confined,digest,write,verify_package
from editorial import validate_claims,validate_document,validate_schema,DOCUMENT,preview
from factory import validate_brief

class Contracts(unittest.TestCase):
    def test_example_brief(self):
        brief,sources=validate_brief(Path(__file__).resolve().parents[1]/'examples/videoops-launch.json')
        self.assertEqual(len(sources),2)
        self.assertIn('constraints',brief)

    def test_path_escape(self):
        with tempfile.TemporaryDirectory() as d:
            for p in ['../secret','/etc/passwd','a/../../b']:
                with self.assertRaises(ValueError):confined(d,p)
            Path(d,'link').symlink_to('/tmp')
            with self.assertRaises(ValueError):confined(d,'link/anything')

    def test_exact_support(self):
        sources={'source':{'text':'Observed setup was five minutes.'}}
        claim={'id':'setup','text':'Setup was five minutes.','sourceId':'source','quote':'Observed setup was five minutes.','qualification':'one observation'}
        validate_claims([claim],sources)
        for field,value in [('quote','Setup takes three minutes everywhere.'),('sourceId','missing'),('id','../../escape')]:
            changed={**claim,field:value}
            with self.assertRaises(ValueError):validate_claims([changed],sources)
        with self.assertRaises(ValueError):validate_claims([claim,claim],sources)

    def test_document_citations(self):
        doc={'title':'Hello','blocks':[{'text':'A fact','claimIds':['known']}]}
        validate_document(doc,[{'id':'known'}])
        with self.assertRaises(ValueError):validate_document(doc,[{'id':'different'}])
        with self.assertRaises(ValueError):validate_schema({**doc,'command':'rm -rf /'},DOCUMENT)

    def test_html_escaping(self):
        page=preview({'title':'<script>alert(1)</script>','blocks':[{'text':'<img src=x onerror=alert(1)>','claimIds':[]}]})
        self.assertNotIn('<script>',page)
        self.assertNotIn('<img',page)
        self.assertIn('&lt;script&gt;',page)

    def test_package_drift(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=write(root/'output/article.md','original')
            write(root/'output/package.json',{'schema':'kujo.publishing-house-factory.package/v1','files':[{'path':'output/article.md','sha256':digest(p)}]})
            self.assertEqual(len(verify_package(root)),64)
            p.write_text('changed')
            with self.assertRaisesRegex(ValueError,'drift'):verify_package(root)

    def test_missing_source_and_bad_url(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=write(root/'source.txt','A preserved source.')
            base={'schema':'kujo.publishing-house-factory.brief/v1','title':'Example','audience':'Readers','objective':'Explain','voice':'Direct','constraints':[],'sources':[{'id':'a','path':'source.txt','url':'https://example.com/source'}]}
            p=write(root/'brief.json',base)
            validate_brief(p)
            base['sources'][0]['url']='javascript:alert(1)';write(p,base)
            with self.assertRaises(ValueError):validate_brief(p)
            base['sources'][0]['url']='https://example.com';source.unlink();write(p,base)
            with self.assertRaises(ValueError):validate_brief(p)

if __name__=='__main__':unittest.main()
