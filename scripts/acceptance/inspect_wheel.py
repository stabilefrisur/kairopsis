"""Record wheel contents and reject accidental runtime/private material."""

import argparse
import hashlib
import json
import posixpath
import re
from email.parser import Parser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit
from zipfile import ZipFile


def inspect(wheel: Path, require_assets: bool, source: Path | None = None) -> dict:
    with ZipFile(wheel) as archive:
        names = sorted(archive.namelist())
        metadata_name = next(name for name in names if name.endswith('.dist-info/METADATA'))
        metadata = Parser().parsestr(archive.read(metadata_name).decode())
        forbidden = []
        for name in names:
            path = PurePosixPath(name)
            if any(part in {'.git', '.scratch', '__pycache__', 'node_modules'} for part in path.parts):
                forbidden.append(name)
            elif path.name in {'.env', 'credentials.json', 'secrets.json', 'workspace.json', 'current.json',
                                'catalogue.json', 'metapyle.json', 'idea.json', 'native.csv', 'derived.csv'} or path.suffix in {'.sqlite', '.sqlite3', '.db', '.pem', '.key'}:
                forbidden.append(name)
            elif path.is_absolute() or '..' in path.parts:
                forbidden.append(name)
        assets = {
            'templates': [name for name in names if '/templates/' in name],
            'javascript': [name for name in names if '/static/' in name and name.endswith('.js')],
            'stylesheets': [name for name in names if '/static/' in name and name.endswith('.css')],
            'licenses': [name for name in names if any(word in name.lower() for word in ('license', 'licence', 'notice'))],
            'fonts_icons': [name for name in names if name.endswith(('.woff', '.woff2', '.ttf', '.svg', '.ico'))],
            'documentation': [name for name in names if name.startswith('kairopsis/docs/') and name.endswith('.md')],
            'skills': [name for name in names if name.startswith('kairopsis/skills/') and not name.endswith('/')],
        }
        vendor_checks = []
        for name in names:
            if name.endswith('/static/vendor/manifest.json'):
                for entry in json.loads(archive.read(name)):
                    asset_path = str(PurePosixPath(name).parent / entry['file'])
                    actual = hashlib.sha256(archive.read(asset_path)).hexdigest() if asset_path in names else None
                    vendor_checks.append({
                        'package': entry['package'], 'version': entry['version'], 'path': asset_path,
                        'expected_sha256': entry['sha256'], 'actual_sha256': actual,
                        'passed': actual == entry['sha256'],
                    })
        missing = [kind for kind in ('templates', 'javascript', 'stylesheets', 'licenses') if not assets[kind]] if require_assets else []
        if require_assets and not vendor_checks:
            missing.append('pinned vendor manifest')
        if require_assets:
            for guide in ('human-guide.md', 'agent-setup.md'):
                if f'kairopsis/docs/{guide}' not in names:
                    missing.append(f'installed guide: {guide}')
            if 'kairopsis/skills/kairopsis-analysis/SKILL.md' not in names:
                missing.append('installed skill: kairopsis-analysis')
        # A copied skill must retain working references without the source checkout.
        skill_checks = []
        for name in assets['skills']:
            if not name.endswith('.md'):
                continue
            root = '/'.join(PurePosixPath(name).parts[:3])
            content = archive.read(name).decode('utf-8')
            for link in re.findall(r'\[[^\]]+\]\(([^)]+)\)', content):
                url = urlsplit(link)
                if url.scheme or url.netloc or not url.path:
                    continue
                target = posixpath.normpath(posixpath.join(posixpath.dirname(name), unquote(url.path)))
                skill_checks.append({'path': name, 'target': target,
                    'passed': target.startswith(root + '/') and target in names})
        source_checks = []
        if source is not None:
            package_source = source / 'src' / 'kairopsis'
            for original in sorted(package_source.rglob('*')):
                if not original.is_file() or '__pycache__' in original.parts or original.suffix in {'.pyc', '.pyo'}:
                    continue
                expected_name = original.relative_to(source / 'src').as_posix()
                if expected_name not in names:
                    missing.append(f'source file: {expected_name}')
            for name in names:
                if name.startswith('kairopsis/') and not name.endswith('/'):
                    original = source / 'src' / name
                    expected = hashlib.sha256(original.read_bytes()).hexdigest() if original.is_file() else None
                    source_checks.append({'path': name, 'source_sha256': expected,
                        'wheel_sha256': hashlib.sha256(archive.read(name)).hexdigest(),
                        'passed': original.is_file() and original.read_bytes() == archive.read(name)})
            readme = source / 'README.md'
            description = metadata.get_payload()
            source_checks.append({'path': 'README.md in package metadata',
                'source_sha256': hashlib.sha256(readme.read_bytes()).hexdigest(),
                'passed': description.strip() == readme.read_text(encoding='utf-8').strip()})
        return {
            'wheel': str(wheel.resolve()),
            'sha256': hashlib.sha256(wheel.read_bytes()).hexdigest(),
            'name': metadata['Name'],
            'version': metadata['Version'],
            'requires_python': metadata['Requires-Python'],
            'direct_dependencies': metadata.get_all('Requires-Dist', []),
            'contents': [{
                'path': name,
                'size': archive.getinfo(name).file_size,
                'sha256': hashlib.sha256(archive.read(name)).hexdigest(),
            } for name in names if not name.endswith('/')],
            'assets': assets,
            'vendor_checks': vendor_checks,
            'source_checks': source_checks,
            'skill_checks': skill_checks,
            'forbidden_paths': forbidden,
            'missing_required_assets': missing,
            'passed': not forbidden and not missing and all(check['passed'] for check in [*vendor_checks, *source_checks, *skill_checks]),
            'limitations': 'Static pathname/content inventory; human review still checks asset versions, licensing and private information inside otherwise legitimate files.',
        }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('wheel', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--require-assets', action='store_true')
    parser.add_argument('--source-directory', type=Path)
    args = parser.parse_args()
    report = inspect(args.wheel, args.require_assets, args.source_directory)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in ('name', 'version', 'passed', 'forbidden_paths', 'missing_required_assets')}))
    raise SystemExit(0 if report['passed'] else 1)
