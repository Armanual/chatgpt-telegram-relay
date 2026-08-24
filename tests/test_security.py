from __future__ import annotations

import unittest

from study_planner_bot.security import bearer_value, constant_time_equal


class SecurityTest(unittest.TestCase):
    def test_constant_time_equal_requires_values(self) -> None:
        self.assertTrue(constant_time_equal("secret", "secret"))
        self.assertFalse(constant_time_equal("secret", "other"))
        self.assertFalse(constant_time_equal(None, "secret"))
        self.assertFalse(constant_time_equal("secret", None))

    def test_bearer_value(self) -> None:
        self.assertEqual(bearer_value("Bearer abc123"), "abc123")
        self.assertIsNone(bearer_value("Token abc123"))
        self.assertIsNone(bearer_value(None))


if __name__ == "__main__":
    unittest.main()

