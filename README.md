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
| `plot_results.py` | PC (Python 3 + matplotlib) | Plots sweep results into `set_vs_measured.png` and `error.png` |
| `set_vs_measured.png`, `error.png` | — | Generated graphs (currently **simulated**, see below) |

## Hardware setup

We have one board, so a single Pico plays both roles:

- "Pico A" = PWM output on GP15 + UART0 (GP0 TX, GP1 RX)
- "Pico B" = PIO edge timer on GP11 + UART1 (GP8 TX, GP9 RX)

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
Timeouts on UART and PIO report which wire to check instead of hanging.

## Running

1. Flash MicroPython onto the Pico and open `main.py` in Thonny.
2. Wire the three jumpers above and run `main.py`.
3. At the prompt, type a duty cycle (1–99) to test one value, or `sweep` to test 1–99 %
   and print CSV.
4. Press Stop / Ctrl+C to end. PWM and PIO are switched off and GP15 is left LOW.

## Plotting results

```
pip install matplotlib
python plot_results.py
```

- If `results.csv` exists, the script plots it. To make it: copy the sweep output from
  Thonny (starting at the line `set,measured,diff`) into `results.csv`.
- If `results.csv` is missing, the script plots **simulated** data from a model of ideal
  hardware (125 MHz clock, PWM counter of 62500 per period, 2-cycle PIO loops). Graph titles
  then say "(SIMULATED)". The current graphs in this repo are simulated and will be
  replaced by a real hardware sweep for the final report.

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

Tools: MicroPython firmware (MIT license), Thonny IDE (MIT license), Git and GitHub.

## Contributions

All code not tagged with a source is the group's own: the PIO edge-timer logic, the UART
message format, error handling, and the sweep. The FIFO clear/restart before each
measurement was Ryan's and Klara's idea.
