import unittest


class TestJobs(unittest.TestCase):
    """测试自动化规则。"""

    def test_repl_name(self):
        """similar_chars不应重复。"""
        from jobs.repl.name import similar_chars

        all_chars = "".join(similar_chars)
        self.assertEqual(len(all_chars), len(set(all_chars)))


if __name__ == "__main__":
    unittest.main()
