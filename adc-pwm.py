from machine import Pin, PWM, ADC
import time

adcA = ADC(Pin(26))
led1 = PWM(Pin(18))
led1.freq(1000)

while True:
	valeur = adcA.read_u16()
	print(valeur)

	led1.duty_u16(valeur)

	time.sleep_ms(50)