import gc
import utime

import ntptime
import machine
import _thread
import time
from pi_pico_w_server_tools.app import App, compose_response, format_dict, load_html
import socket

app = App(hostname="movement_sensor_1")
rtc = machine.RTC()
sensor_pin = machine.Pin(5, machine.Pin.IN)

is_night_mode = False
start_time = None


def get_hour_and_minute(timestamp: tuple):
    hour = timestamp[3]
    minute = timestamp[4]

    if hour < 10:
        hour = f"0{hour}"
    else:
        hour = f"{hour}"

    if minute < 10:
        minute = f"0{minute}"
    else:
        minute = f"{minute}"

    return f"{hour}:{minute}"


def parse_hour_and_minute(data: str):
    data = data.split(":")
    hour = int(data[0])
    minute = int(data[1])

    return (0, 0, 0, hour, minute, 0, 0, 0)


def time_str():
    t = utime.localtime()
    dt = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
        t[0], t[1], t[2], t[3], t[4], t[5]
    )
    return dt


def seconds_elapsed_to_str(elapsed_seconds: int):
    days = elapsed_seconds // (60 * 60 * 24)
    elapsed_seconds -= days * 60 * 60 * 24

    hours = elapsed_seconds // (60 * 60)
    elapsed_seconds -= hours * 60 * 60

    minutes = elapsed_seconds // 60
    elapsed_seconds -= minutes * 60

    seconds = int(elapsed_seconds % 60)

    return f"{days}d {hours}h {minutes}m {seconds}s"


def home_page(cl: socket.socket, parameters: dict):
    cl.sendall(
        compose_response(
            response=format_dict(
                load_html("static/index.html"),
                {
                    "uptime": seconds_elapsed_to_str(
                        datetime_diff_seconds(utime.localtime(), app.server_start_time)
                    ),
                    "local_time": time_str(),
                },
            )
        )
    )


def toggle_sensor(cl: socket.socket, parameters: dict):
    emit_signal()
    cl.sendall(compose_response())


def synch_time(rtc, timezone_offset=1):
    ntptime.settime()

    t = time.time() + (60 * (60 * timezone_offset))
    tm = time.localtime(t)

    rtc.datetime(
        (tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0)  # weekday (1–7)
    )


def datetime_diff_seconds(timestamp_a, timestamp_b):

    t1 = utime.mktime(timestamp_a)
    t2 = utime.mktime(timestamp_b)  
    return t1 - t2


central_url: str = "http://192.168.1.14/v1/connect"

import requests


def emit_signal():

    try:
        resp = requests.get(f"{central_url}?host_name={app.hostname}&ip={app.ip}")

        print(resp.status_code)
        print(resp.content)
        resp.close()

    except Exception as err:
        print(f"error: {str(err)}")
    gc.collect()


def sensor_loop():
    while 1 < 2:
        if sensor_pin.value() == 0:
            # print(sensor_pin.value())
            emit_signal()

        time.sleep(1)


if __name__ == "__main__":

    synch_time(rtc)
    app.register_endpoint("/v1", home_page)
    app.register_endpoint("/v1/toggle_sensor", toggle_sensor)

    _thread.start_new_thread(sensor_loop, ())
    try:
        app.main_loop()
    except (KeyboardInterrupt, Exception) as ex:
        print(f"Server error type: {type(ex)}\tmessage: {ex}\texiting")
