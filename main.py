import json
import utime

import requests

import ntptime
import machine
import _thread
import time
from pi_pico_w_server_tools.app import App, compose_response, format_dict, load_html
import socket
app = App(hostname="movement_sensor_toilet.local")
rtc = machine.RTC()     
sensor_pin = machine.Pin(5, machine.Pin.IN)

is_night_mode = False
start_time = None

listeners = []


def get_hour_and_minute(timestamp:tuple):
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

def parse_hour_and_minute(data:str):
    data = data.split(":")
    hour = int(data[0])
    minute = int(data[1])
    
    return (0,0,0,hour,minute,0,0,0)

def time_str():
    t = utime.localtime()
    dt = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
    t[0], t[1], t[2], t[3], t[4], t[5]
)
    return dt

def seconds_elapsed_to_str(elapsed_seconds:int):
    days = elapsed_seconds // (60 * 60 * 24)
    elapsed_seconds  -= (days * 60 * 60 * 24)
    
    hours = elapsed_seconds // (60 * 60)
    elapsed_seconds -= (hours* 60 * 60)
    
    minutes = elapsed_seconds // 60
    elapsed_seconds -= (minutes * 60)
    
    seconds = int(elapsed_seconds % 60)
    
    return f"{days}d {hours}h {minutes}m {seconds}s"
    
def home_page(cl: socket.socket, parameters: dict):    
    cl.sendall(compose_response(response=format_dict(load_html("static/index.html"),
    {
        "uptime":seconds_elapsed_to_str(datetime_diff_seconds(utime.localtime(), start_time)),
        "local_time" : time_str(),
    }
)))
    
    
def load_listeners() -> list[str]:
    global listeners
    # TODO improve error description
    try:
        with open("listeners.json", "r") as file:
            listeners = json.loads(file.read())
            print(f"loaded listeners: {listeners}")

    except Exception as err:
        print("listeners.json file error")
        raise Exception("listeners.json file error")

    try:
        listeners = [url for url in listeners]
    except ValueError as err:
        print(f"listeners configuration error: {str(err)}")
            
    return listeners

def save_listeners(
    current_config: list[str], old_config: list[str]
):

    # for wifi in wifi_config:
    #     if wifi != current_config:
    #         new_config.append(wifi)
    #         new_config_dict.append(wifi.to_dict())
    if len(current_config) == len(old_config) and all([new == old for new, old in zip(current_config, old_config)]):
        print("wifi_config is already up to date")
        return

    # TODO improve error description
    try:
        print("updating wifi_config file")
        with open("wifi_config.json", "w") as file:
            file.write(json.dumps(current_config))
            file.flush()
        return
    except Exception:
        print("wifi_config.json file error")
        raise Exception("wifi_config.json file error")
    
def add_listener(cl: socket.socket, parameters: dict):
    global listeners
    
    new_listener = parameters.get('listener', None)
    if new_listener == None:
        cl.sendall(compose_response())
    
    listeners.append(new_listener)
    save_listeners(listeners, load_listeners())
    

def toggle_sensor(cl: socket.socket, parameters: dict):
    emit_signals()
    cl.sendall(compose_response())

def status(cl: socket.socket, parameters: dict):
    cl.sendall(compose_response())

def synch_time(rtc, timezone_offset = 1):
    ntptime.settime()
    
    t = time.time() + (60 * (60 * timezone_offset))
    tm = time.localtime(t)
    
    rtc.datetime((
    tm[0], tm[1], tm[2],
    tm[6] + 1,        # weekday (1–7)
    tm[3], tm[4], tm[5], 0
))
    

def datetime_diff_seconds(timestamp_a,timestamp_b):
    
    t1 = utime.mktime(timestamp_a)
    t2 = utime.mktime(timestamp_b)
    return t1 - t2
    
def emit_signals():
    global listeners

    try:
        for endpoint in listeners:
            requests.get(endpoint, timeout=3)
    except Exception as ex:
        pass
        # print("error occurred")

def sensor_loop():
    while 1<2:
        
        if (sensor_pin.value() == 1 ):
            # print("now")
            emit_signals()
        time.sleep(0.1)
      
if __name__ == "__main__":

    synch_time(rtc)
    start_time = time.localtime()
    app.register_endpoint("/v1", home_page)
    app.register_endpoint("/v1/status", status)
    # app.register_endpoint("/v1/save_settings", save_settings)
    app.register_endpoint("/v1/toggle_sensor", toggle_sensor)
    
    load_listeners()
    _thread.start_new_thread(sensor_loop, ())
    try:
        app.main_loop()
    except (KeyboardInterrupt, Exception) as ex:
        print(f"Server error type: {type(ex)}\tmessage: {ex}\texiting")