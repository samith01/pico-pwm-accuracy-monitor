# I2C signal pins
I2C_SDA = 14
I2C_SCL = 15

# ADS 1015 configuration information
ADS1015_ADDR = 0x48
ADS1015_PWM = 2     # port 2 has (low-pass filtered) PWM signal

from machine import Pin, ADC, I2C
# You will need to upload the file ads1x15.py to the pico for the following code to work properly
from ads1x15 import ADS1015

i2c = I2C(1, sda=Pin(I2C_SDA), scl=Pin(I2C_SCL))
adc = ADS1015(i2c, ADS1015_ADDR, 1)

# scan i2c bus to get a listing of all I2C devices... including the ADC that has the servo feedback values
addresses = i2c.scan()
for address in addresses:
	print(hex(address))


# Read filtered PWM input from the header
value = adc.read(0, ADS1015_PWM)
print(value)