"""Verify the wheel outside the checkout, reusing the current dependency environment.

The package is installed into an isolated target; imports must resolve to that
wheel installation. No network, model weights, or editable source imports needed.
"""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
wheel = root / "dist" / "driftlab-0.1.0-py3-none-any.whl"
with tempfile.TemporaryDirectory(prefix="driftlab-wheel-check-") as directory:
    target = Path(directory) / "installed"
    subprocess.run([sys.executable,"-m","pip","install","--no-deps","--target",str(target),str(wheel),"--disable-pip-version-check"],check=True)
    code = r'''
from pathlib import Path
import json
import re
import sys
sys.path.insert(0,sys.argv[1])
import driftlab
assert Path(driftlab.__file__).is_relative_to(Path(sys.argv[1])), driftlab.__file__
from driftlab import DriftLab
from driftlab.api.main import app
from fastapi.testclient import TestClient
client=TestClient(app)
response=client.get('/app/')
assert response.status_code==200
script=re.search(r'src="([^\"]+\.js)"',response.text).group(1)
assert client.get(script).status_code==200
lab=DriftLab(sys.argv[2])
try:
    b=lab.run(repeats=5,seed=42)
    c=lab.run(repeats=5,seed=91,run_type='candidate',mock_profile='regression')
    comparison=lab.compare(b.run_id,c.run_id)
    assert comparison['recommendation']=='block'
    assert len(lab.get_run(b.run_id)['observations'])==160
    assert len(comparison['verdicts'])==4
    json.dumps(comparison,allow_nan=False)
    print('PASS: installed wheel imports, bundled dashboard/assets, 320 generations, persisted drift evidence')
finally:
    lab.close()
'''
    env = {**os.environ,"DRIFTLAB_WORKSPACE":str(Path(directory)/"workspace")}
    subprocess.run([sys.executable,"-I","-c",code,str(target),str(Path(directory)/"workspace")],cwd=directory,env=env,check=True)
