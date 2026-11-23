# SPDX-License-Identifier: BSD-2-Clause-Patent
"""Every file git tracks, or would track, is printable ASCII; only LICENSES/ is exempt."""
import os
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLOWED = b'\t\r\n' + bytes(range(0x20, 0x7f))


def first_bad_line(path):
    """Line number of the first byte outside tab, CR, LF and printable ASCII, or None."""
    with open(path, 'rb') as f:
        data = f.read()
    if not data.translate(None, ALLOWED):
        return None
    for line, text in enumerate(data.split(b'\n'), 1):
        if text.translate(None, ALLOWED):
            return line


def candidate_files():
    """Tracked files and untracked files that are not ignored, relative to the root."""
    out = subprocess.run(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
                         cwd=ROOT, capture_output=True, check=True).stdout
    return [p.decode('utf-8', 'surrogateescape') for p in out.split(b'\0') if p]


class AsciiTest(unittest.TestCase):
    def test_check_flags_a_planted_byte(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'f')
            with open(path, 'wb') as f:
                f.write(b'plain\nx\xe2\x80\x9cy\n')
            self.assertEqual(first_bad_line(path), 2)
            with open(path, 'wb') as f:
                f.write(b'plain\tascii\r\n')
            self.assertIsNone(first_bad_line(path))

    def test_tree_is_ascii(self):
        bad = []
        for name in candidate_files():
            path = os.path.join(ROOT, name)
            if not name.isascii():
                bad.append(name.encode('ascii', 'backslashreplace').decode())
            elif not name.startswith('LICENSES/') and os.path.isfile(path):
                line = first_bad_line(path)
                if line:
                    bad.append(f'{name}:{line}')
        self.assertEqual(bad, [])


if __name__ == '__main__':
    unittest.main()
