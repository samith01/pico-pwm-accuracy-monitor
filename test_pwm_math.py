# test_pwm_math.py - unit tests that run on the PC, no Pico needed
# SED 1115 Group 5 - Samith Fernando, Ryan Hannum Horne, Klara Kerekes
#
# Run from this folder with:   python -m unittest -v
#
# These test the calculations in pwm_math.py (the same file main.py uses on
# the Pico) and the ideal-hardware model in plot_results.py. The tests that
# need the real board are in board_test.py.
#
# Source:
#   [S1] Python unittest module (TestCase, assertEqual, assertAlmostEqual):
#        https://docs.python.org/3/library/unittest.html
import unittest
from pwm_math import (duty_to_u16, counts_to_duty, average_duty, format_message,
                      parse_message, parse_duty_input, error_stats)
from plot_results import simulate


class TestPwmMath(unittest.TestCase):   # [S1]

    # ---- duty_to_u16: percent -> 0-65535 ----
    def test_duty_to_u16_ends(self):
        self.assertEqual(duty_to_u16(0), 0)
        self.assertEqual(duty_to_u16(100), 65535)

    def test_duty_to_u16_middle(self):
        self.assertEqual(duty_to_u16(50), 32767)   # 32767.5 rounds down (int)
        self.assertEqual(duty_to_u16(25), 16383)

    def test_duty_to_u16_always_goes_up(self):
        # a higher duty must never give a lower duty_u16
        values = [duty_to_u16(d) for d in range(0, 101)]
        self.assertEqual(values, sorted(values))

    # ---- counts_to_duty / average_duty: PIO counts -> percent ----
    def test_counts_to_duty(self):
        self.assertEqual(counts_to_duty(1, 1), 50)
        self.assertEqual(counts_to_duty(1, 3), 25)
        self.assertAlmostEqual(counts_to_duty(15625, 46875), 25.0)  # real-size counts

    def test_counts_to_duty_no_signal(self):
        self.assertIsNone(counts_to_duty(0, 0))

    def test_average_duty(self):
        self.assertEqual(average_duty([(1, 1), (1, 3)]), 37.5)   # (50 + 25) / 2

    def test_average_duty_bad_input(self):
        self.assertIsNone(average_duty([]))
        self.assertIsNone(average_duty([(1, 1), (0, 0)]))

    # ---- UART message format ----
    def test_format_message(self):
        self.assertEqual(format_message(30), "30.0000\n")
        self.assertEqual(format_message(-1), "-1.0000\n")   # B's "could not measure"

    def test_message_round_trip(self):
        for value in (1, 12.5, 50, 99, -1):
            sent = format_message(value).encode()   # UART sends bytes
            self.assertAlmostEqual(parse_message(sent), value)

    def test_parse_message_bad_data(self):
        self.assertIsNone(parse_message(None))        # readline() timed out
        self.assertIsNone(parse_message(b""))
        self.assertIsNone(parse_message(b"3o.0\n"))   # corrupted byte
        self.assertIsNone(parse_message(b"\xff\xfe"))  # not valid text at all

    # ---- user input checking ----
    def test_valid_input(self):
        self.assertEqual(parse_duty_input("50"), (50.0, None))
        self.assertEqual(parse_duty_input(" 12.5 "), (12.5, None))
        self.assertEqual(parse_duty_input("1"), (1.0, None))     # lowest allowed
        self.assertEqual(parse_duty_input("99"), (99.0, None))   # highest allowed

    def test_input_not_a_number(self):
        for text in ("abc", "", "50%", "5 0"):
            duty, problem = parse_duty_input(text)
            self.assertIsNone(duty)
            self.assertIn("valid number", problem)

    def test_input_out_of_range(self):
        for text in ("0", "100", "-5", "0.5", "99.5", "nan", "inf"):
            duty, problem = parse_duty_input(text)
            self.assertIsNone(duty)
            self.assertIn("1-99", problem)

    # ---- sweep summary ----
    def test_error_stats(self):
        mean_err, worst, worst_duty = error_stats([(10, 10.1), (50, 49.7), (90, 90.0)])
        self.assertAlmostEqual(mean_err, 0.4 / 3)
        self.assertAlmostEqual(worst, 0.3)
        self.assertEqual(worst_duty, 50)

    def test_error_stats_empty(self):
        self.assertIsNone(error_stats([]))

    # ---- ideal-hardware model ----
    def test_simulated_sweep_is_accurate(self):
        # On ideal hardware the only errors are duty_u16 rounding and the
        # 2-clock PIO offset, so every point should be within 0.01 points.
        results = simulate()
        self.assertEqual(len(results), 99)
        for set_duty, measured in results:
            self.assertAlmostEqual(measured, set_duty, delta=0.01)


if __name__ == "__main__":
    unittest.main()
