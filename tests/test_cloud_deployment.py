"""Cloud safety and packaging tests do not need a cloud account."""
from pathlib import Path
import tarfile

import pytest
import yaml

ROOT=Path(__file__).resolve().parents[1]


def test_cloud_has_only_loopback_web_and_low_memory_settings():
    model=yaml.safe_load((ROOT/'docker-compose.cloud.yml').read_text(encoding='utf-8'))
    services=model['services']
    assert not services['postgres'].get('ports') and not services['api'].get('ports')
    assert services['web']['ports']==['127.0.0.1:${CLOUD_WEB_PORT:-8080}:80']
    assert services['api']['environment']['MAX_GENERATIONS']=='1'
    assert services['api']['environment']['AUTH_COOKIE_SECURE']=='false'
    assert services['api']['environment']['HF_HUB_OFFLINE']=='1'
    assert 'postgres_data' in model['volumes'] and 'huggingface_cache' in model['volumes']


def test_cpu_dockerfile_matches_pinned_torch():
    dockerfile=(ROOT/'Dockerfile').read_text(encoding='utf-8')
    pin=next(line.split('==')[1] for line in (ROOT/'requirements.txt').read_text(encoding='utf-8').splitlines() if line.startswith('torch=='))
    assert f'ARG TORCH_VERSION={pin}' in dockerfile
    assert 'https://download.pytorch.org/whl/cpu' in dockerfile
    assert 'torch.version.cuda is None' in dockerfile


def test_generation_limit_is_configurable_and_positive(monkeypatch):
    from app.config import AppSettings
    monkeypatch.setenv('MAX_GENERATIONS','1')
    assert AppSettings().max_generations==1
    with pytest.raises(ValueError):
        AppSettings(max_generations=0)


def test_release_bundle_excludes_credentials_data_and_local_dependencies(tmp_path):
    from scripts.package_cloud import package_source
    root=tmp_path/'source'
    for name in ('Dockerfile','.dockerignore','requirements.txt','docker-compose.cloud.yml','app/main.py',
                 'frontend/src/main.tsx','frontend/node_modules/private.txt','.env','.env.cloud',
                 'data/private.pdf','app/__pycache__/cached.pyc'):
        target=root/name
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text('private-value' if name.startswith('.env') else 'source',encoding='utf-8')
    output=tmp_path/'release.tar.gz'
    package_source(root,output)
    with tarfile.open(output) as archive:
        names=archive.getnames()
    assert 'app/main.py' in names and 'frontend/src/main.tsx' in names
    assert '.dockerignore' in names
    assert not any('.env' in name or 'node_modules' in name or '__pycache__' in name or name.startswith('data/') for name in names)


def test_restore_rejects_business_database_and_existing_target_before_restoring(tmp_path,monkeypatch):
    from scripts.cloud_deploy import restore_database
    import subprocess
    calls=[]
    backup=tmp_path/'backup.dump'
    backup.write_bytes(b'PGDMP-test')
    def fail_existing(command,**kwargs):
        calls.append(command)
        raise subprocess.CalledProcessError(1,command)
    monkeypatch.setattr(subprocess,'run',fail_existing)
    with pytest.raises(ValueError):
        restore_database(['docker','exec','test'],'owner','rag_cloud','rag_cloud',backup)
    assert calls==[]
    with pytest.raises(subprocess.CalledProcessError):
        restore_database(['docker','exec','test'],'owner','rag_cloud','rag_restore_probe',backup)
    assert len(calls)==1 and 'createdb' in calls[0] and 'pg_restore' not in calls[0]
