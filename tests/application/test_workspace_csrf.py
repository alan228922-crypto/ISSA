"""CSRF transport accepts Django-rendered token with nondefault cookie names."""
from pathlib import Path
import json
import subprocess


def test_workspace_uses_rendered_csrf_token_before_default_cookie():
    module=(Path(__file__).resolve().parents[2]/'projects/static/projects/workspace/api.js').as_uri()
    script=f'''import {{postJson}} from {json.dumps(module)};
const calls=[];globalThis.fetch=async (url,options)=>{{calls.push(options);return {{json:async()=>({{ok:true}})}}}};
await postJson('/model/check/',{{expected_draft_version:1}},{{cookie:'issa_phase2b1_csrf=private-cookie',querySelector:()=>({{content:'masked-rendered-token'}})}});
await postJson('/model/check/',{{}},{{cookie:'csrftoken=legacy-default'}});
console.log(JSON.stringify(calls.map(c=>({{token:c.headers['X-CSRFToken'],body:JSON.parse(c.body),credentials:c.credentials,method:c.method}}))));'''
    result=subprocess.run(['node','--input-type=module','-e',script],text=True,capture_output=True)
    assert result.returncode==0,result.stderr
    rows=json.loads(result.stdout)
    assert rows[0]=={'token':'masked-rendered-token','body':{'expected_draft_version':1},'credentials':'same-origin','method':'POST'}
    assert rows[1]['token']=='legacy-default'
