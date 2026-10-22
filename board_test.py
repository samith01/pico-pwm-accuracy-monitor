# board_test.py - hardware tests that run ON the Pico
# SED 1115 Group 5 - Samith Fernando, Ryan Hannum Horne, Klara Kerekes
#
# Upload main.py, pwm_math.py and this file to the Pico, wire the three jumpers
# (see main.py), then run this file in Thonny. It runs every test below,
# prints PASS/FAIL for each one and saves the full sweep to results.csv on the
# Pico. Download results.csv to the PC and run plot_results.py to get the
# graphs from real measurements.
#
# The calculations themselves are unit tested on the PC in test_pwm_math.py.
# This file checks that the real hardware (PWM, PIO, UART, wires) works.
#
# Source:
#   [S1] MicroPython docs, built-in open() and file write:
#        https://docs.micropython.org/en/latest/library/builtins.html
import main
from pwm_math import error_stats

# How far (in percentage points) a measurement may be from the set duty and
# still pass. The ideal-hardware model in plot_results.py is off by less than
# 0.002 points, so 0.1 leaves plenty of room for real-board noise. If the board
# turns out to be consistently a bit further off, this is the number to tune.
TOLERANCE = 0.1


class BoardTest:
    SPOT_DUTIES = (10, 25, 50, 75, 90)   # the duties from our status report
    REPEATS = 10                         # how many times to repeat one duty

    def __init__(self):
        self.passed = 0
        self.failed = 0

    def check(self, name, ok, detail=""):
        """Record and print one test result."""
        if ok:
            self.passed += 1
        else:
            self.failed += 1
        print("%s  %s  %s" % ("PASS" if ok else "FAIL", name, detail))

    def test_spot_checks(self):
        """Set a few duty cycles and check each measurement is within TOLERANCE."""
        print("\n--- Spot checks ---")
        for duty in self.SPOT_DUTIES:
            measured = main.run_once(duty, verbose=False)
            if measured is None:
                self.check("duty %d %%" % duty, False, "no measurement")
            else:
                diff = measured - duty
                self.check("duty %d %%" % duty, abs(diff) <= TOLERANCE,
                           "measured %.4f, diff %+.4f" % (measured, diff))

    def test_repeatability(self):
        """Measure the same duty several times; the readings should barely change."""
        print("\n--- Repeatability (50 %% x %d) ---" % self.REPEATS)
        readings = []
        for _ in range(self.REPEATS):
            measured = main.run_once(50, verbose=False)
            if measured is not None:
                readings.append(measured)
        if len(readings) < self.REPEATS:
            self.check("repeatability", False,
                       "only %d of %d readings came back" % (len(readings), self.REPEATS))
            return
        spread = max(readings) - min(readings)
        self.check("repeatability", spread <= TOLERANCE,
                   "min %.4f, max %.4f, spread %.4f" % (min(readings), max(readings), spread))

    def test_sweep(self):
        """Run the full 1-99 % sweep, save it to results.csv and check the worst error."""
        print("\n--- Full sweep 1-99 % ---")
        results = main.sweep()
        with open("results.csv", "w") as f:       # [S1]
            f.write("set,measured,diff\n")
            for duty, measured in results:
                f.write("%d,%.4f,%.4f\n" % (duty, measured, measured - duty))
        print("Saved %d rows to results.csv on the Pico" % len(results))

        self.check("sweep complete", len(results) == 99,
                   "%d of 99 duties measured" % len(results))
        if results:
            mean_err, worst, worst_duty = error_stats(results)
            self.check("sweep accuracy", worst <= TOLERANCE,
                       "mean error %.4f, worst %.4f at %d %%" % (mean_err, worst, worst_duty))

    def test_unplugged_wires(self):
        """Optional manual test: unplug each wire and check the program reports
        it (by naming the wire) instead of hanging or giving a wrong number."""
        print("\n--- Unplugged wire test (manual) ---")
        if input("Run it? Type y, or just press Enter to skip: ").strip().lower() != "y":
            print("skipped")
            return
        for wire in ("GP15->GP11", "GP0->GP9", "GP8->GP1"):
            input("Unplug %s, then press Enter" % wire)
            measured = main.run_once(50, verbose=False)
            self.check("unplugged " + wire, measured is None,
                       "error reported" if measured is None else "got %.4f" % measured)
            input("Plug %s back in, then press Enter" % wire)

    def run_all(self):
        self.test_spot_checks()
        self.test_repeatability()
        self.test_sweep()
        self.test_unplugged_wires()
        print("\n%d passed, %d failed" % (self.passed, self.failed))


try:
    BoardTest().run_all()
finally:
    main.shutdown()      # always switch PWM and PIO off, even after Ctrl+C
