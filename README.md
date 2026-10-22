# Pico PWM Accuracy Monitor

SED 1115 Pair-Based Project, Group 5: Samith Fernando, Ryan Hannum Horne, Klara Kerekes.

One Raspberry Pi Pico ("Pico A") outputs a PWM signal at a chosen duty cycle and sends the
desired value over UART. A second Pico ("Pico B") measures the real duty cycle with a PIO
edge timer and sends the measurement back. Both sides print the difference between the
desired and measured values.

## Files

| File | Runs on | Purpose |
|------|---------|---------|
| `main.py` | Pico (MicroPython) | PWM output, PIO measurement, UART link, interactive prompt and sweep |
| `pwm_math.py` | Pico and PC | The calculations (duty conversion, PIO counts to percent, UART message format, input checking, error stats). No hardware code, so it can be unit tested on a PC |
| `board_test.py` | Pico | `BoardTest` class: hardware tests with PASS/FAIL, saves the sweep to `results.csv` |
| `test_pwm_math.py` | PC | `TestPwmMath` class: unit tests for `pwm_math.py` and the simulation model |
| `plot_results.py` | PC (Python 3 + matplotlib) | Plots `results.csv` into `set_vs_measured.png` and `error.png` and prints the error summary |
| `set_vs_measured.png`, `error.png` | — | Generated graphs. The graph title says whether they come from the board or the simulation |

## Hardware setup

`ROLE` at the top of `main.py` picks the setup:

- `"both"` (default): one Pico plays both roles.
  - "Pico A" = PWM output on GP15 + UART0 (GP0 TX, GP1 RX)
  - "Pico B" = PIO edge timer on GP11 + UART1 (GP8 TX, GP9 RX)
- `"A"` / `"B"`: two Picos. Put `main.py` and `pwm_math.py` on both boards, set
  `ROLE = "A"` on the sender and `ROLE = "B"` on the receiver. Start B first.
  The pins are the same, so the same three wires go between the boards, plus GND to GND.

Three jumper wires:

| From | To | Carries |
|------|----|---------|
| GP15 (A PWM out) | GP11 (B PIO in) | The PWM signal |
| GP0 (A UART0 TX) | GP9 (B UART1 RX) | Desired duty, A to B |
| GP8 (B UART1 TX) | GP1 (A UART0 RX) | Measured duty, B to A |

## How it works

1. **PWM (Pico A):** `machine.PWM` at a fixed 1 kHz. Duty in percent is converted to
   `duty_u16` (0–65535).
2. **UART message:** the desired duty is sent as text with a newline, e.g. `30.0000\n`,
   at 9600 baud.
3. **PIO measurement (Pico B):** a small PIO program waits for a rising edge, then counts
   while the pin is HIGH and while it is LOW. Both counting loops take 2 clock cycles, so
   `duty = high / (high + low) * 100`. The result is averaged over `SAMPLES` periods.
   Before each measurement the state machine is paused, its FIFO cleared and restarted,
   so old readings are never mixed in.
4. **Reply:** Pico B sends the measured duty back (or `-1` if no PWM edges were seen).
   Pico A prints desired, measured and difference.

Duty cycles 0 % and 100 % are rejected: a flat signal has no edges for the PIO to time.
Timeouts on UART and PIO report which wire to check instead of hanging. GP11 has a
pull-down, so an unplugged PWM wire reads as "no edges" instead of random noise.

## Running

1. Flash MicroPython onto the Pico. In Thonny, upload `main.py` and `pwm_math.py` to it.
2. Wire the three jumpers above and run `main.py`.
3. At the prompt, type a duty cycle (1–99) to test one value, or `sweep` to test 1–99 %
   and print CSV.
4. Press Stop / Ctrl+C to end. PWM and PIO are switched off and GP15 is left LOW.

## Testing

There are two kinds of tests.

**Unit tests (PC, no board needed).** `test_pwm_math.py` tests every function in
`pwm_math.py` (normal values, edge values like 1 % and 99 %, and bad input like letters,
`nan`, corrupted UART bytes) and checks the ideal-hardware model is within 0.01 points.
Only the standard library is needed:

```
python -m unittest -v
```

**Hardware tests (on the Pico).** Upload `board_test.py` too and run it in Thonny.
The `BoardTest` class runs:

| Test | What it checks | Pass if |
|------|----------------|---------|
| Spot checks | 10, 25, 50, 75, 90 % | each within `TOLERANCE` (0.1 points) |
| Repeatability | 50 % measured 10 times | spread (max − min) within 0.1 points |
| Full sweep | every duty 1–99 % | all 99 measured, worst error within 0.1 points |
| Unplugged wires (optional, manual) | unplug each of the three wires in turn | program reports an error naming the wire, no hang |

It prints PASS/FAIL for each and a total, and saves the sweep to `results.csv` on the Pico.

## Plotting results

1. Run `board_test.py` on the Pico (above).
2. In Thonny, open View > Files, right-click `results.csv` on the Pico side and choose
   Download, into this folder.
3. Run:

```
pip install matplotlib
python plot_results.py
```

The script prints the mean and largest error and saves both graphs, titled
"(measured on board)". If `results.csv` is missing it plots **simulated** data from a
model of ideal hardware instead (125 MHz clock, PWM counter of 62500 per period, 2-cycle
PIO loops) and the titles say "(SIMULATED)". On ideal hardware the largest error is
0.0016 points.

## Results

`results.csv` is a real sweep from the board (1–99 %, 1 kHz, 100 periods averaged per
point). The graphs in this repo are made from it.

- All 99 duty cycles were measured.
- Mean absolute error: **0.0108** percentage points.
- Largest error: **0.0319** percentage points (at 47 %).
- Every point is within the 0.1-point `TOLERANCE` used by `board_test.py`.

The error is spread evenly above and below zero with no trend across the range, so it
looks like small period-to-period noise rather than a fixed offset. It is about 20 times
the ideal-hardware model's 0.0016 points, but still well under 0.1 points.

## References

Code sources (tagged in the code comments as `[S#]`):

1. MicroPython developers. (n.d.). *machine.PWM – pulse width modulation*. MicroPython documentation. https://docs.micropython.org/en/latest/library/machine.PWM.html
2. MicroPython developers. (n.d.). *rp2 – functionality specific to the RP2040*. MicroPython documentation. https://docs.micropython.org/en/latest/library/rp2.html
3. MicroPython developers. (n.d.). *class StateMachine – access to the RP2040's programmable I/O interface*. MicroPython documentation. https://docs.micropython.org/en/latest/library/rp2.StateMachine.html
4. Raspberry Pi Ltd. (n.d.). *RP2040 Datasheet*, Chapter 3 (PIO) and Section 4.5 (PWM). https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf
5. Raspberry Pi Ltd. (n.d.). *Raspberry Pi Pico Python SDK*, Section 3.9 (Programmable IO). https://datasheets.raspberrypi.com/pico/raspberry-pi-pico-python-sdk.pdf
6. MicroPython developers. (n.d.). *rp2 PIO examples*. GitHub. https://github.com/micropython/micropython/tree/master/examples/rp2
7. MicroPython developers. (n.d.). *machine.UART – duplex serial communication bus*. MicroPython documentation. https://docs.micropython.org/en/latest/library/machine.UART.html
8. MicroPython developers. (n.d.). *time – time related functions*. MicroPython documentation. https://docs.micropython.org/en/latest/library/time.html
9. Raspberry Pi Ltd. (n.d.). *Raspberry Pi Pico pinout*. https://datasheets.raspberrypi.com/pico/Pico-R3-A4-Pinout.pdf
10. MicroPython developers. (n.d.). *ports/rp2/machine_pwm.c*. GitHub. https://github.com/micropython/micropython/blob/master/ports/rp2/machine_pwm.c
11. Python Software Foundation. (n.d.). *csv – CSV file reading and writing*. https://docs.python.org/3/library/csv.html
12. Matplotlib development team. (n.d.). *matplotlib.pyplot*. https://matplotlib.org/stable/api/pyplot_summary.html
13. Python Software Foundation. (n.d.). *unittest – Unit testing framework*. https://docs.python.org/3/library/unittest.html
14. MicroPython developers. (n.d.). *builtins – builtin functions and exceptions* (`open`). https://docs.micropython.org/en/latest/library/builtins.html

Tools: MicroPython firmware (MIT license), Thonny IDE (MIT license), Git and GitHub.

## Contributions

All code not tagged with a source is the group's own: the PIO edge-timer logic, the UART
message format, error handling, and the sweep. The FIFO clear/restart before each
measurement was Ryan's and Klara's idea.
