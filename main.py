import network
from utime import sleep, sleep_ms, localtime
import machine
import secrets

import pimoroni_i2c
import breakout_scd41
import ubinascii

from umqtt.robust import MQTTClient

import ussl
import ntptime

CLIENT_ID = ubinascii.hexlify(machine.unique_id()).decode("utf-8")

led = machine.Pin("LED", machine.Pin.OUT)

def connect():
    print(f'Connecting WiFI \'{secrets.WIFI_SSID}\'...')
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(secrets.WIFI_SSID, secrets.WIFI_PASSWORD)
    while wlan.isconnected() == False:
        led.toggle()
        sleep(1)
    ip = wlan.ifconfig()[0]
    led.on()
    print(f'Connected on \'{ip}\'')


def start():
    i2c = pimoroni_i2c.PimoroniI2C(4, 5)
    breakout_scd41.init(i2c)
    breakout_scd41.start()

    with open("cert.der", 'rb') as f:
        cacert = f.read()
    f.close()

    ssl_params = {
        'server_side': False,
        'key': None,
        'cert': None,
        'cert_reqs': ussl.CERT_REQUIRED,
        'cadata': cacert,
        'server_hostname': secrets.MQTT_HOST}

    print(f'MQTT client \'{CLIENT_ID}\' connecting to \'{secrets.MQTT_HOST}\' as user \'{secrets.MQTT_USER}\'...')

    c = MQTTClient(
        client_id = CLIENT_ID,
        server = secrets.MQTT_HOST,
        port = 8883,
        ssl = True,
        ssl_params = ssl_params,
        user = secrets.MQTT_USER,
        password = secrets.MQTT_PASS,
        keepalive=3600)
    c.connect()

    while True:
        if breakout_scd41.ready():
            co2, temperature, humidity = breakout_scd41.measure()
            c.publish(f'{CLIENT_ID}/data', f'{{"co2": {co2}, "temp": {temperature}, "humidity": {humidity}}}')
            led.off()
            sleep_ms(100)
            led.on()
            sleep(1 * 60)

try:
    connect()

    print('Sync''ing time...')
    ntptime.settime()
    print(f'Current time is \'{localtime()}\'.')

    start()

except KeyboardInterrupt:
    machine.reset()
