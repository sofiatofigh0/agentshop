"""The cached prefixes must come out byte-identical in every process.

A prompt cache is a prefix match: one byte that differs between two runs and
the whole ~14k-token experience bank is written again at full price, with no
error to say so. The usual cause is not an edit but a build step that is not
deterministic — iterating a set, a dict built in hash order. Hash
randomization makes exactly that differ between processes, so building the
prefixes under two different seeds and comparing them catches it here rather
than on the bill.
"""

import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DIGEST = """
import hashlib, json
import agent, application_generator as gen, tools
for text in (gen.STABLE_PREFIX, agent.SYSTEM_PROMPT, json.dumps(tools.TOOLS)):
    print(hashlib.sha256(text.encode()).hexdigest())
"""


def digests(seed: str) -> list:
    env = {**os.environ, "PYTHONHASHSEED": seed}
    out = subprocess.run([sys.executable, "-c", DIGEST], cwd=ROOT, env=env,
                         capture_output=True, text=True, check=True)
    return out.stdout.split()


class PrefixDeterminism(unittest.TestCase):
    def test_same_bytes_under_different_hash_seeds(self):
        first, second = digests("1"), digests("2")
        self.assertEqual(len(first), 3)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
