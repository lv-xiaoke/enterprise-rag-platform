"""Export allowlisted source and one public BGE cache; never export .env/data."""
import argparse
from pathlib import Path
import tarfile

ROOT=Path(__file__).resolve().parents[1]
MODEL='models--BAAI--bge-small-zh-v1.5'
FILES=('Dockerfile','requirements.txt','docker-compose.cloud.yml','.dockerignore',
       'alembic.ini','frontend/Dockerfile','frontend/nginx.conf','frontend/package.json',
       'frontend/package-lock.json','frontend/tsconfig.json','frontend/vite.config.ts',
       'frontend/index.html','scripts/assign_legacy_knowledge_bases.py',
       'scripts/cloud_deploy.py','scripts/package_cloud.py','deploy/README.md')


def package_source(root: Path, output: Path):
    paths=[root/name for name in FILES if (root/name).is_file()]
    for directory in ('app','migrations','frontend/src'):
        paths.extend(path for path in (root/directory).rglob('*') if path.is_file())
    output.parent.mkdir(parents=True,exist_ok=True)
    with tarfile.open(output,'x:gz') as archive:
        for path in sorted(set(paths)):
            relative=path.relative_to(root)
            if path.is_symlink() or any((part.startswith('.') and part!='.dockerignore') or part in {'__pycache__','test'} for part in relative.parts):
                continue
            if path.suffix in {'.pyc','.pyo'} or '.test.' in path.name:
                continue
            archive.add(path,arcname=relative.as_posix(),recursive=False)


def package_model(cache: Path, output: Path):
    model=cache/MODEL
    if not (model/'snapshots').is_dir() or not (model/'refs/main').is_file():
        raise ValueError('Expected a complete cached BGE model')
    # Resolve every link first; a public model export must not follow a link
    # into unrelated models, user tokens or other host files.
    for path in model.rglob('*'):
        if not path.resolve().is_relative_to(model.resolve()):
            raise ValueError('Model cache link leaves the selected model')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tarfile.open(output,'x:gz',dereference=True) as archive:
        archive.add(model,arcname=f'hub/{MODEL}')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind',choices=['source','model'])
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--cache',type=Path,default=Path.home()/'.cache/huggingface/hub')
    args=parser.parse_args()
    if args.kind=='source':
        package_source(ROOT,args.output)
    else:
        package_model(args.cache,args.output)
    print(f'Created {args.output}; no environment file included.')


if __name__=='__main__':
    main()
