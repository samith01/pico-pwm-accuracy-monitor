# pwm_math.py - the calculations behind the PWM accuracy monitor
# SED 1115 Group 5 - Samith Fernando, Ryan Hannum Horne, Klara Kerekes
#
# None of these functions touch the hardware, so the same file runs on the
# Pico (imported by main.py) and on a PC (imported by test_pwm_math.py and
# plot_results.py). That is what lets us unit test the logic without a board.
#
# Sources:
#   [S1] MicroPython docs, machine.PWM (duty_u16 range 0-65535):
#        https://docs.micropython.org/en/latest/library/machine.PWM.html

MIN_DUTY = 1    # 0 % and 100 % are flat signals with no edges for the PIO to time
MAX_DUTY = 99


def duty_to_u16(percent):
    """Convert a duty cycle in percent (0-100) to the 0-65535 value duty_u16 wants [S1]."""
    return int(percent * 65535 / 100)


def counts_to_duty(high, low):
    """Duty cycle in percent from one PIO reading (HIGH count and LOW count).
    Both PIO loops take 2 clock cycles, so the counts are in the same unit.
    Returns None if both counts are 0 (nothing was measured)."""
    if high + low == 0:
        return None
    return high * 100 / (high + low)


def average_duty(pairs):
    """Average duty cycle over a list of (high, low) pairs, one pair per PWM period.
    Returns None if the list is empty or any pair is unusable."""
    if not pairs:
        return None
    total = 0
    for high, low in pairs:
        duty = counts_to_duty(high, low)
        if duty is None:
            return None
        total += duty
    return total / len(pairs)


def format_message(value):
    """Turn a number into the text we send over UART, e.g. 30 -> '30.0000\\n'."""
    return "%.4f\n" % value


def parse_message(line):
    """Turn a received UART line back into a number.
    uart.readline() gives bytes, or None if nothing came in.
    Returns None for empty, cut-off or corrupt messages instead of crashing."""
    if line is None:
        return None
    try:
        if isinstance(line, bytes):
            line = line.decode()
        return float(line.strip())
    except (ValueError, UnicodeError):
        return None


def parse_duty_input(text):
    """Check what the user typed at the prompt.
    Returns (duty, None) if it is a valid duty cycle,
    or (None, message) explaining what is wrong."""
    try:
        duty = float(text.strip())
    except ValueError:
        return None, "Please enter a valid number (no letters or symbols)."
    # "nan" and "inf" convert to float but fail this range check too
    if not MIN_DUTY <= duty <= MAX_DUTY:
        return None, "Duty cycle has to be from %d-%d percent." % (MIN_DUTY, MAX_DUTY)
    return duty, None


def error_stats(results):
    """Summary of a sweep. results is a list of (set_duty, measured_duty).
    Returns (mean absolute error, largest absolute error, duty where it happened),
    all in percentage points, or None if there are no results."""
    if not results:
        return None
    total = 0
    worst = 0
    worst_duty = results[0][0]
    for set_duty, measured in results:
        err = abs(measured - set_duty)
        total += err
        if err > worst:
            worst = err
            worst_duty = set_duty
    return total / len(results), worst, worst_duty
