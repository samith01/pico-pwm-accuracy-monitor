# main.py - Pico PWM Accuracy Monitor (one-board version)
# SED 1115 Group 5 - Samith Fernando, Ryan Hannum Horne, Klara Kerekes
#
# What it does:
#   Pico A sets a PWM duty cycle and sends the desired value over UART.
#   Pico B measures the real duty cycle with PIO edge timing and sends it back.
#   Both sides print the difference between desired and measured.
#
# We only have one board, so one Pico plays both roles:
#   "Pico A" = PWM output on GP15 + UART0
#   "Pico B" = PIO edge timer on GP11 + UART1
#
# Wires (3 jumpers on the same Pico):
#   GP15 (A PWM out)  -> GP11 (B PIO in)    carries the PWM signal itself
#   GP0  (A UART0 TX) -> GP9  (B UART1 RX)  A sends the desired duty to B
#   GP8  (B UART1 TX) -> GP1  (A UART0 RX)  B sends the measured duty back to A
#
# Usage in Thonny: type a duty cycle (1-99) to test one value,
# or type "sweep" to test 1-99 % and print CSV for plot_results.py.
# Press Ctrl+C (Stop) to end; PWM and PIO are switched off cleanly.
#
# Sources (cited in the code as [S#]):
#   [S1] MicroPython docs, machine.PWM (freq, duty_u16, deinit):
#        https://docs.micropython.org/en/latest/library/machine.PWM.html
#   [S2] MicroPython docs, rp2 module (@rp2.asm_pio, PIO instructions):
#        https://docs.micropython.org/en/latest/library/rp2.html
#   [S3] MicroPython docs, rp2.StateMachine (in_base, jmp_pin, rx_fifo, get, restart):
#        https://docs.micropython.org/en/latest/library/rp2.StateMachine.html
#   [S4] RP2040 Datasheet, ch. 3 "PIO" (wait/jmp/mov/push, x-- counting loop,
#        mov x, ~null): https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf
#   [S5] Raspberry Pi Pico Python SDK, section 3.9 "Programmable IO":
#        https://datasheets.raspberrypi.com/pico/raspberry-pi-pico-python-sdk.pdf
#   [S6] MicroPython rp2 PIO examples (decorator/StateMachine pattern):
#        https://github.com/micropython/micropython/tree/master/examples/rp2
#   [S7] MicroPython docs, machine.UART (UART(id, baudrate, tx, rx), any, readline):
#        https://docs.micropython.org/en/latest/library/machine.UART.html
#   [S8] MicroPython docs, time (ticks_ms, ticks_diff for timeouts):
#        https://docs.micropython.org/en/latest/library/time.html
#   [S9] Raspberry Pi Pico pinout (GP0/GP1 = UART0, GP8/GP9 = UART1):
#        https://datasheets.raspberrypi.com/pico/Pico-R3-A4-Pinout.pdf

# Everything not marked with [S#] is the group's own code (PIO edge-timer
# logic, message format, error handling, sweep). The FIFO clear/restart in
# pio_duty() was suggested by Ryan and Klara.
from machine import Pin, PWM, UART
import rp2
import time

PWM_PIN = 15         # Pico A: PWM output pin
MEASURE_PIN = 11     # Pico B: PIO input pin
PWM_FREQ = 1000      # Hz, fixed frequency (only duty changes)
SAMPLES = 10         # PWM periods averaged per measurement (raise to 100 for final tests)


# ======================================================================
# Pico A: PWM output
# ======================================================================
pwm = PWM(Pin(PWM_PIN))          # [S1]
pwm.freq(PWM_FREQ)


def set_duty(percent):
    """Set PWM duty in percent (0-100). duty_u16 uses 0-65535 for 0-100 % [S1]."""
    pwm.duty_u16(int(percent * 65535 / 100))


# ======================================================================
# Pico B: PIO edge timer
# ======================================================================
# A small program that runs on the PIO hardware, separate from Python.
# It works like a stopwatch: counts while the pin is HIGH, then while it is LOW.
# Each counting loop takes exactly 2 clock cycles, so the two counts use the
# same unit and duty = high / (high + low).
# PIO can only count DOWN, so counters start at 0xFFFFFFFF and Python flips them.
# Instruction set and the x-- loop idea: [S4]; @rp2.asm_pio syntax: [S2], [S5], [S6].
@rp2.asm_pio()
def edge_timer():
    wait(0, pin, 0)              # wait for pin LOW...
    wait(1, pin, 0)              # ...then HIGH: a pulse just started (rising edge)
    mov(x, invert(null))         # x = 0xFFFFFFFF (counter for HIGH time)
    label("high")
    jmp(x_dec, "high_next")      # x -= 1
    label("high_next")
    jmp(pin, "high")             # keep counting while pin is HIGH
    mov(y, x)                    # pin went LOW: save HIGH count in y
    mov(x, invert(null))         # reset x for LOW time
    label("low")
    jmp(pin, "done")             # pin went HIGH again: one full period finished
    jmp(x_dec, "low")            # x -= 1, keep counting while pin is LOW
    label("done")
    mov(isr, y)                  # send HIGH count to Python
    push()
    mov(isr, x)                  # send LOW count to Python
    push()


measure_pin = Pin(MEASURE_PIN, Pin.IN)
# jmp_pin lets "jmp(pin, ...)" check GP11; in_base lets "wait(..., pin, 0)" watch GP11
sm = rp2.StateMachine(0, edge_timer, in_base=measure_pin, jmp_pin=measure_pin)  # [S3]
sm.active(1)


def read_pair(timeout_ms):
    """Wait for one (high, low) count pair from the PIO.
    Returns None if no edges arrive in time (0 %, 100 %, or wire unplugged)."""
    start = time.ticks_ms()
    while sm.rx_fifo() < 2:      # need both counts in the receive queue
        if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
            return None
    high = 0xFFFFFFFF - sm.get()  # flip count-down value into a normal count
    low = 0xFFFFFFFF - sm.get()
    return high, low


def pio_duty(samples=SAMPLES, timeout_ms=100):
    """Measure duty in percent, averaged over several PWM periods.
    Returns None if no PWM edges are seen."""
    # Pause, clear old readings, restart, resume, so every reading belongs to
    # the current duty and starts on a fresh rising edge. (Ryan/Klara's idea)
    sm.active(0)
    while sm.rx_fifo():
        sm.get()
    sm.restart()
    sm.active(1)

    total = 0
    for _ in range(samples):
        pair = read_pair(timeout_ms)
        if pair is None:
            return None
        high, low = pair
        total += high * 100 / (high + low)  # duty (%) = active time / period * 100
    return total / samples


# ======================================================================
# UART link (UART0 = Pico A, UART1 = Pico B)
# ======================================================================
# Message format: one number as text, ending in a newline, e.g. "30.0000\n"
# UART setup [S7]; pins [S9]; ticks_ms/ticks_diff timeouts [S8].
uart_a = UART(0, baudrate=9600, tx=Pin(0), rx=Pin(1))
uart_b = UART(1, baudrate=9600, tx=Pin(8), rx=Pin(9))


def read_line(uart, timeout_ms=1000):
    """Read one number from a UART. Returns None on timeout or corrupt data."""
    start = time.ticks_ms()
    while not uart.any():
        if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
            return None
    time.sleep_ms(20)            # let the rest of the line arrive
    line = uart.readline()
    try:
        return float(line.decode().strip())
    except (ValueError, AttributeError):
        return None


def pico_b_step(verbose):
    """Pico B's job: receive desired duty, measure PWM, send measurement back.
    Sends -1 if the PWM could not be measured."""
    desired = read_line(uart_b)
    if desired is None:
        print("B: message not received - check GP0->GP9")
        return
    measured = pio_duty()
    if measured is None:
        print("B: no PWM edges - check GP15->GP11")
        measured = -1
    uart_b.write("%.4f\n" % measured)
    if verbose:
        print("B: desired %.2f  measured %.4f  diff %+.4f" % (desired, measured, measured - desired))


def run_once(duty, verbose=True):
    """One full round trip: A sets PWM and sends, B measures and replies, A compares.
    Returns the measured duty, or None on any error."""
    set_duty(duty)
    time.sleep_ms(50)            # let PWM settle on the new duty
    uart_a.write("%.4f\n" % duty)
    pico_b_step(verbose)         # on two boards this runs on Pico B instead
    measured = read_line(uart_a)
    if measured is None:
        print("A: message not received - check GP8->GP1")
        return None
    if measured < 0:
        print("A: B could not measure PWM edges")
        return None
    if verbose:
        print("A: desired %.2f  measured %.4f  diff %+.4f" % (duty, measured, measured - duty))
    return measured


def sweep():
    """Test every duty from 1 to 99 % and print CSV (copy into results.csv)."""
    print("set,measured,diff")
    for duty in range(1, 100):
        measured = run_once(duty, verbose=False)
        if measured is not None:
            print("%d,%.4f,%.4f" % (duty, measured, measured - duty))


# ======================================================================
# Main loop
# ======================================================================
try:
    while True:
        user_input = input("Duty cycle (1-99) or 'sweep': ").strip()
        if user_input == "sweep":
            sweep()
            continue
        try:
            duty = float(user_input)
        except ValueError:
            print("Please enter a valid number (no letters or symbols).")
            continue
        if not 1 <= duty <= 99:  # 0 and 100 % have no edges for the PIO to time
            print("Duty cycle has to be from 1-99 percent.")
            continue
        run_once(duty)
finally:
    # Clean shutdown on Stop/Ctrl+C: stop PIO, stop PWM, leave GP15 LOW
    sm.active(0)
    pwm.deinit()
    Pin(PWM_PIN, Pin.OUT).value(0)
    print("Stopped. PWM and PIO switched off.")
