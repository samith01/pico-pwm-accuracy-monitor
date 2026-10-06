# plot_results.py - runs on the PC (not the Pico)
# SED 1115 Group 5 - Samith Fernando, Ryan Hannum Horne, Klara Kerekes
#
# 1. In Thonny, run main.py and type "sweep".
# 2. Copy the CSV lines (starting with "set,measured,diff") into results.csv.
# 3. Run this script; it saves set_vs_measured.png and error.png.
#
# If results.csv does not exist, the script plots SIMULATED data instead
# (see simulate() below) and every graph title says "SIMULATED".
# Simulated graphs show what the ideal hardware should give; they are not
# measurements and must be replaced by a real sweep for the final report.
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
import matplotlib.pyplot as plt

CLOCK_HZ = 125_000_000  # RP2040 default system clock [S4]
PWM_FREQ = 1000         # same as main.py


def simulate():
    """Model of main.py on ideal hardware, for duty 1-99 %.
    PWM: 125 MHz / 1 kHz = 125000 clocks per period; MicroPython picks
    divider 2 and top+1 = 62500 counts [S3]. duty_u16 is turned into a
    compare value cc, so the pin is HIGH for cc*2 clocks.
    PIO: each counting loop is 2 instructions = 2 clocks [S4]; the LOW loop
    starts 2 clocks late (mov y,x and mov x,~null), so subtract those."""
    period = CLOCK_HZ // PWM_FREQ
    div = 2
    top1 = period // div
    rows = []
    for duty in range(1, 100):
        duty_u16 = int(duty * 65535 / 100)            # same formula as main.py
        cc = (duty_u16 * top1 + 65535 // 2) // 65535  # rounding as in [S3]
        high_clk = cc * div
        low_clk = period - high_clk
        high = high_clk // 2
        low = (low_clk - 2) // 2
        measured = high * 100 / (high + low)
        rows.append({"set": duty, "measured": measured, "diff": measured - duty})
    return rows


# Read the sweep results: set duty, measured duty, difference [S1]
if os.path.exists("results.csv"):
    with open("results.csv") as f:
        rows = list(csv.DictReader(f))
    tag = ""
else:
    rows = simulate()
    tag = " (SIMULATED)"
set_vals = [float(r["set"]) for r in rows]
measured = [float(r["measured"]) for r in rows]
diff = [float(r["diff"]) for r in rows]

# Graph 1: measured vs set, with the ideal line (measured = set) [S2]
plt.figure()
plt.plot(set_vals, set_vals, "--", color="gray", label="ideal (measured = set)")
plt.plot(set_vals, measured, "o", markersize=3, label="measured (PIO)")
plt.xlabel("Set duty cycle (%)")
plt.ylabel("Measured duty cycle (%)")
plt.title("Set vs measured PWM duty cycle (1 kHz)" + tag)
plt.legend()
plt.grid(True)
plt.savefig("set_vs_measured.png", dpi=150, bbox_inches="tight")

# Graph 2: error (measured - set) at each duty cycle [S2]
plt.figure()
plt.plot(set_vals, diff, "o-", markersize=3)
plt.axhline(0, color="gray", linestyle="--")
plt.xlabel("Set duty cycle (%)")
plt.ylabel("Difference (percentage points)")
plt.title("Measurement error across duty cycles" + tag)
plt.grid(True)
plt.savefig("error.png", dpi=150, bbox_inches="tight")
print("Saved set_vs_measured.png and error.png" + tag)
