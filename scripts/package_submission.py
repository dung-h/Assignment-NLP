"""Create a review archive containing runtime code/data/tests and required outputs."""

import argparse
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', default='course-assistant-preview.zip')
    parser.add_argument('--include-report', action='store_true')
    args = parser.parse_args()
    if Path(args.name).name != args.name or not args.name.endswith('.zip'):
        parser.error('--name must be a .zip filename without a directory')
    selected = set()
    for folder in ('src', 'data', 'contracts', 'tests', 'input'):
        for path in (ROOT / folder).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix not in {'.pyc', '.pyo'}:
                selected.add(path)
    for name in ('README.md', 'requirements.txt', 'Dockerfile', '.dockerignore', 'pytest.ini', 'app.py'):
        selected.add(ROOT / name)
    for name in ('export_required_outputs.py', 'run_samples.py', 'evaluate_gold.py', 'verify_outputs.py', 'package_submission.py'):
        selected.add(ROOT / 'scripts' / name)
    for name in ('grammar.txt', 'samples.txt', 'parse-results.txt', 'semantic.txt', 'intent-entity.txt',
                 'query.txt', 'retrieval.txt', 'answer.txt', 'dialogue.txt', 'evaluation.txt',
                 'gold_results.json', 'end_to_end_results.json'):
        selected.add(ROOT / 'output' / name)
    if args.include_report:
        selected.add(ROOT / 'report' / 'COURSE_ASSISTANT_REPORT.pdf')
    missing = [path.relative_to(ROOT).as_posix() for path in selected if not path.is_file()]
    if missing:
        raise FileNotFoundError(f'Required submission artifacts are missing: {missing}')
    destination = ROOT / 'dist' / args.name
    destination.parent.mkdir(exist_ok=True)
    if destination.exists():
        raise FileExistsError(f'Review archive already exists: {destination}; choose another --name')
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(selected):
            archive.write(path, 'project/' + path.relative_to(ROOT).as_posix())
    print(f'Created {destination.relative_to(ROOT)} ({destination.stat().st_size} bytes, {len(selected)} files)')


if __name__ == '__main__':
    main()
