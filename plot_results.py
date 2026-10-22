# plot_results.py - runs on the PC (not the Pico)
# SED 1115 Group 5 - Samith Fernando, Ryan Hannum Horne, Klara Kerekes
#
# 1. In Thonny, run board_test.py on the Pico. It saves results.csv on the Pico.
#    (Or run main.py, type "sweep" and copy the CSV lines into results.csv.)
# 2. Download results.csv into this folder (Thonny: View > Files, right-click
#    results.csv on the Pico side > Download).
# 3. Run this script; it saves set_vs_measured.png and error.png and prints
#    the mean and largest error.
#
# If results.csv does not exist, the script plots SIMULATED data instead
# (see simulate() below) and every graph title says "SIMULATED".
# Simulated graphs show what the ideal hardware should give; they are not
# measurements.
#
# Sources:
#   [S1] Python csv module (DictReader):
#        https://docs.python.org/3/library/csv.html
#   [S2] Matplotlib pyplot API (figure, plot, axhline, savefig):
#        https://matplotlib.org/stable/api/pyplot_summary.html
#   [S3] MicroPython rp2 PWM driver, ports/rp2/machine_pwm.c (how duty_u16
#        becomes a counter compare value):
#        https://github.com/micropython/micropython/blob/master/ports/rp2/machine_pwm.c
#   [S4] RP2040 Datasheet, ch. 3 (PIO, 1 instruction per clock) and 4.5 (PWM):
#        https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf
import csv
import os
from pwm_math import duty_to_u16, counts_to_duty, error_stats

CLOCK_HZ = 125_000_000  # RP2040 default system clock [S4]
PWM_FREQ = 1000         # same as main.py


def simulate():
    """Model of main.py on ideal hardware, for duty 1-99 %.
    PWM: 125 MHz / 1 kHz = 125000 clocks per period; MicroPython picks
    divider 2 and top+1 = 62500 counts [S3]. duty_u16 is turned into a
    compare value cc, so the pin is HIGH for cc*2 clocks.
    PIO: each counting loop is 2 instructions = 2 clocks [S4]; the LOW loop
    starts 2 clocks late (mov y,x and mov x,~null), so subtract those.
    Returns a list of (set, measured)."""
    period = CLOCK_HZ // PWM_FREQ
    div = 2
    top1 = period // div
    results = []
    for duty in range(1, 100):
        duty_u16 = duty_to_u16(duty)                  # same formula as main.py
        cc = (duty_u16 * top1 + 65535 // 2) // 65535  # rounding as in [S3]
        high_clk = cc * div
        low_clk = period - high_clk
        high = high_clk // 2
        low = (low_clk - 2) // 2
        results.append((duty, counts_to_duty(high, low)))
    return results


def read_results(path):
    """Read a sweep CSV (columns set,measured,diff) into a list of (set, measured) [S1]."""
    with open(path) as f:
        return [(float(r["set"]), float(r["measured"])) for r in csv.DictReader(f)]


def plot(results, tag):
    """Save the two graphs [S2]."""
    import matplotlib.pyplot as plt   # imported here so the unit tests don't need matplotlib

    set_vals = [s for s, m in results]
    measured = [m for s, m in results]
    diff = [m - s for s, m in results]

    # Graph 1: measured vs set, with the ideal line (measured = set)
    plt.figure()
    plt.plot(set_vals, set_vals, "--", color="gray", label="ideal (measured = set)")
    plt.plot(set_vals, measured, "o", markersize=3, label="measured (PIO)")
    plt.xlabel("Set duty cycle (%)")
    plt.ylabel("Measured duty cycle (%)")
    plt.title("Set vs measured PWM duty cycle (1 kHz)" + tag)
    plt.legend()
    plt.grid(True)
    plt.savefig("set_vs_measured.png", dpi=150, bbox_inches="tight")

    # Graph 2: error (measured - set) at each duty cycle
    plt.figure()
    plt.plot(set_vals, diff, "o-", markersize=3)
    plt.axhline(0, color="gray", linestyle="--")
    plt.xlabel("Set duty cycle (%)")
    plt.ylabel("Difference (percentage points)")
    plt.title("Measurement error across duty cycles" + tag)
    plt.grid(True)
    plt.savefig("error.png", dpi=150, bbox_inches="tight")


if __name__ == "__main__":
    if os.path.exists("results.csv"):
        results = read_results("results.csv")
        tag = " (measured on board)"
    else:
        results = simulate()
        tag = " (SIMULATED)"
    mean_err, worst, worst_duty = error_stats(results)
    print("%d points%s" % (len(results), tag))
    print("Mean absolute error: %.4f percentage points" % mean_err)
    print("Largest error: %.4f percentage points at %g %% duty" % (worst, worst_duty))
    plot(results, tag)
    print("Saved set_vs_measured.png and error.png")
