"""SSH-only demo operations. No provisioning, payment, deletion or data reset."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
PROJECT='rag-cloud-demo'


def compose_command(env_file: Path):
    return ['docker','compose','-p',PROJECT,'--project-directory',str(ROOT),
            '--env-file',str(env_file.resolve()),'-f',str(ROOT/'docker-compose.cloud.yml')]


def command_environment():
    # Shell interpolation wins over --env-file; do not accidentally inject
    # local test/development credentials into the cloud stack.
    return {key:value for key,value in os.environ.items()
            if not key.startswith(('POSTGRES_','LLM_','AUTH_','RAG_'))
            and key not in {'APP_ORIGIN','RELEASE_TAG','CLOUD_WEB_PORT'}}


def load_config(base):
    result=subprocess.run(base+['config','--format','json'],env=command_environment(),
                          capture_output=True,text=True)
    if result.returncode:
        raise ValueError('Cloud configuration invalid; check required private environment values')
    model=json.loads(result.stdout)
    services=model['services']
    settings=services['api']['environment']
    if not all(settings.get(key) for key in ('LLM_API_KEY','LLM_BASE_URL','LLM_MODEL')):
        raise ValueError('All three LLM settings are required')
    database=services['postgres']['environment']
    if len(database.get('POSTGRES_PASSWORD',''))<24:
        raise ValueError('Use a generated database password of at least 24 characters')
    for key in ('POSTGRES_DB','POSTGRES_USER'):
        if not re.fullmatch('[a-z][a-z0-9_]{0,62}',database[key]):
            raise ValueError(f'Invalid database identifier: {key}')
    origin=urlsplit(settings['APP_ORIGIN'])
    if origin.scheme!='http' or origin.hostname not in {'localhost','127.0.0.1'} or origin.username or origin.password or origin.query or origin.fragment or origin.path not in ('','/'):
        raise ValueError('This trial profile requires a loopback HTTP origin over SSH')
    if settings.get('AUTH_COOKIE_SECURE')!='false':
        raise ValueError('Loopback HTTP requires AUTH_COOKIE_SECURE=false')
    if services['postgres'].get('ports') or services['api'].get('ports'):
        raise ValueError('Database and API must not publish host ports')
    if any(port.get('host_ip')!='127.0.0.1' for port in services['web'].get('ports',[])):
        raise ValueError('Web must bind only to 127.0.0.1')
    return model


def backup_database(prefix, user, database, output: Path):
    output.parent.mkdir(parents=True,exist_ok=True)
    # x mode protects existing backups; restrictive permissions on Linux.
    descriptor=os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(descriptor,'wb') as target:
        subprocess.run(prefix+['pg_dump','-U',user,'-d',database,'-Fc'],stdout=target,check=True)
    with output.open('rb') as source:
        if source.read(5)!=b'PGDMP':
            raise ValueError('Backup is not a PostgreSQL custom dump; retain it for diagnosis')


def restore_database(prefix, user, source_database, destination, backup: Path):
    if destination==source_database or not re.fullmatch('rag_restore_[a-z0-9_]{1,45}',destination):
        raise ValueError('Restore only to a new rag_restore_* database')
    if not backup.is_file():
        raise ValueError('Backup does not exist')
    # createdb fails for existing names. Never drop, clean or overwrite a DB.
    subprocess.run(prefix+['createdb','-U',user,destination],check=True)
    with backup.open('rb') as source:
        subprocess.run(prefix+['pg_restore','-U',user,'-d',destination,'--exit-on-error',
                              '--single-transaction','--no-owner','--no-privileges'],stdin=source,check=True)
    subprocess.run(prefix+['psql','-U',user,'-d',destination,'-c',
                          'SELECT version_num FROM alembic_version; SELECT count(*) AS restored_chunks FROM chunks;'],check=True)


def init_environment(destination: Path):
    # Only this local preparation step needs python-dotenv, already installed
    # by this repo. The server's standard-library CLI never imports it.
    from dotenv import dotenv_values, set_key
    existing=dotenv_values(ROOT/'.env')
    keys=('LLM_API_KEY','LLM_BASE_URL','LLM_MODEL')
    if not all(existing.get(key) for key in keys):
        raise ValueError('Configure the existing local .env model settings first')
    values={key:existing[key] for key in keys}
    values.update(POSTGRES_DB='rag_cloud',POSTGRES_USER='rag_cloud',
                  POSTGRES_PASSWORD=secrets.token_urlsafe(32),
                  RELEASE_TAG='cloud-'+datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S'),
                  CLOUD_WEB_PORT='8080',APP_ORIGIN='http://127.0.0.1:18080')
    descriptor=os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(descriptor,'w',encoding='utf-8') as target:
        target.write('# Private cloud environment; do not commit or put in source bundles.\n')
    for key,value in values.items():
        set_key(destination,key,value)
    if os.name!='nt':
        destination.chmod(0o600)
    print('Private environment created. Existing files are never overwritten.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['init','validate','build','seed-model','up','status','logs','backup','restore'])
    parser.add_argument('--env-file',type=Path,default=ROOT/'.env.cloud')
    parser.add_argument('--archive',type=Path)
    parser.add_argument('--database')
    args=parser.parse_args()
    if args.action=='init':
        init_environment(args.env_file)
        return
    base=compose_command(args.env_file)
    model=load_config(base)  # No config dump: it contains credentials.
    environment=command_environment()
    if args.action=='validate':
        print('Validated: private loopback Web, internal DB/API, complete model configuration.')
    elif args.action=='build':
        subprocess.run(base+['build','api','web'],env=environment,check=True)
    elif args.action=='seed-model':
        if not args.archive or not args.archive.is_file():
            raise ValueError('Provide the exported BGE archive with --archive')
        code=("import tarfile; "
              "a=tarfile.open('/tmp/bge-cache.tar.gz'); "
              "assert all(m.name.startswith('hub/models--BAAI--bge-small-zh-v1.5') for m in a.getmembers()); "
              "a.extractall('/root/.cache/huggingface',filter='data'); print('BGE cache imported')")
        subprocess.run(base+['run','--rm','--no-deps','-T','--entrypoint','python','-v',
                            str(args.archive.resolve())+':/tmp/bge-cache.tar.gz:ro','api','-c',code],env=environment,check=True)
    elif args.action=='up':
        subprocess.run(base+['up','-d','--no-build','--wait','--wait-timeout','180'],env=environment,check=True)
    elif args.action in {'status','logs'}:
        command=['ps','--all'] if args.action=='status' else ['logs','--since','10m','api']
        subprocess.run(base+command,env=environment,check=True)
    else:
        settings=model['services']['postgres']['environment']
        prefix=base+['exec','-T','postgres']
        # Pass the same sanitized environment to child pg commands.
        for key in list(os.environ):
            if key not in environment:
                os.environ.pop(key)
        if args.action=='backup':
            output=ROOT/'backups'/('cloud-'+datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')+'.dump')
            backup_database(prefix,settings['POSTGRES_USER'],settings['POSTGRES_DB'],output)
            print(f'Backup created: {output.name}; verify with restore before relying on it.')
        else:
            if not args.archive or not args.database:
                raise ValueError('Restore requires --archive and a new --database rag_restore_* name')
            restore_database(prefix,settings['POSTGRES_USER'],settings['POSTGRES_DB'],args.database,args.archive)


if __name__=='__main__':
    try:
        main()
    except (ValueError,OSError,subprocess.CalledProcessError):
        # Neither the config model nor a subprocess failure may echo secrets.
        print('Operation failed. Check the selected action, private configuration and service state.')
        raise SystemExit(1)
