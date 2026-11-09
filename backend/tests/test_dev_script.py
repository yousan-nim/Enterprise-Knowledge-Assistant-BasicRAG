from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import os


class DevScriptTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / 'scripts').mkdir()
        shutil.copyfile(Path(__file__).resolve().parents[2] / 'scripts/dev.sh', self.root / 'scripts/dev.sh')
        (self.root / 'bin').mkdir()
        fake = self.root / 'bin/docker'
        fake.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$DOCKER_TEST_LOG"\nif [ "$1" = info ] && [ "${DOCKER_TEST_DOWN:-0}" = 1 ]; then exit 1; fi\n')
        fake.chmod(0o755)
        self.env = {**os.environ, 'PATH': str(self.root / 'bin') + os.pathsep + os.environ['PATH'], 'DOCKER_TEST_LOG': str(self.root / 'calls')}

    def run_script(self):
        return subprocess.run(['sh', str(self.root / 'scripts/dev.sh')], cwd='/', env=self.env, capture_output=True, text=True)

    def test_generates_private_env_and_starts_stack(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        settings = dict(line.split('=', 1) for line in (self.root / '.env').read_text().splitlines())
        self.assertEqual(len(settings['POSTGRES_PASSWORD']), 48)
        self.assertEqual((self.root / '.env').stat().st_mode & 0o777, 0o600)
        self.assertIn('compose up -d --build --wait --wait-timeout 1800 frontend', (self.root / 'calls').read_text())
        self.assertNotIn(settings['POSTGRES_PASSWORD'], result.stdout)

    def test_preserves_existing_env(self):
        (self.root / '.env').write_text('POSTGRES_PASSWORD=existing\n')
        self.assertEqual(self.run_script().returncode, 0)
        self.assertEqual((self.root / '.env').read_text(), 'POSTGRES_PASSWORD=existing\n')

    def test_stopped_docker_fails_without_creating_env(self):
        self.env['DOCKER_TEST_DOWN'] = '1'
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Start Docker Desktop', result.stderr)
        self.assertFalse((self.root / '.env').exists())
