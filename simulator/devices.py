import time
import json
import argparse
import ssl
import paho.mqtt.client as mqtt

BROKER = "localhost"
PORT = 8883

DEVICES = {
    "door_sensor": {"topic": "house/doors/main", "type": "sensor", "value": "CLOSED", "password": "pass6"},
    "window_1": {"topic": "house/windows/w1", "type": "sensor", "value": "CLOSED", "password": "pass1"},
    "motion_yard": {"topic": "house/yard/motion", "type": "sensor", "value": "OFF", "password": "pass7"},
    "smoke_detector": {"topic": "house/hall/smoke", "type": "sensor", "value": "OFF", "password": "pass2"},
    "keypad": {"topic": "house/hall/keypad", "type": "sensor", "value": "", "password": "pass3"},
    "siren": {"topic": "house/hall/siren", "type": "actuator", "state": "OFF", "password": "pass4"},
    "lock": {"topic": "house/doors/lock", "type": "actuator", "state": "LOCKED", "password": "pass5"},
    "yard_light": {"topic": "house/yard/light", "type": "actuator", "state": "OFF", "password": "pass8"}
}

clients = {}

def on_connect(client, userdata, flags, rc):
    dev_id = userdata["id"]
    topic_base = DEVICES[dev_id]["topic"]
    if rc == 0:
        print(f"[{dev_id}] Підключено до брокера!")
        client.publish(f"{topic_base}/status", "online", retain=True)
        if DEVICES[dev_id]["type"] == "actuator":
            client.subscribe(f"{topic_base}/set")
            payload = {"state": DEVICES[dev_id]["state"], "ts": int(time.time())}
            client.publish(f"{topic_base}/state", json.dumps(payload), retain=True)

def on_message(client, userdata, msg):
    dev_id = userdata["id"]
    topic_base = DEVICES[dev_id]["topic"]
    try:
        command = json.loads(msg.payload.decode())
        if "state" in command:
            new_state = command["state"]
            DEVICES[dev_id]["state"] = new_state
            print(f"[{dev_id}] Отримано команду: {new_state}")
            state_payload = {"state": new_state, "ts": int(time.time())}
            client.publish(f"{topic_base}/state", json.dumps(state_payload), retain=True)
    except Exception as e:
        print(f"Помилка: {e}")

def setup_clients():
    for dev_id, dev_info in DEVICES.items():
        client = mqtt.Client(userdata={"id": dev_id})
        topic_base = dev_info["topic"]
        client.username_pw_set(username=dev_id, password=dev_info["password"])
        client.tls_set(ca_certs="certs/ca.crt", tls_version=ssl.PROTOCOL_TLSv1_2)
        client.tls_insecure_set(True)
        client.will_set(f"{topic_base}/status", "offline", retain=True)
        client.on_connect = on_connect
        client.on_message = on_message
        client.connect(BROKER, PORT, 60)
        client.loop_start()
        clients[dev_id] = client

def run_scenario(scenario):
    print(f"Запуск сценарію: {scenario}")
    ts = int(time.time())
    if scenario == "break_in":
        DEVICES['window_1']['value'] = "OPEN" 
        payload = {"value": "OPEN", "ts": ts}
        clients["window_1"].publish(f"{DEVICES['window_1']['topic']}/telemetry", json.dumps(payload))
        print("Сценарій: Вікно 1 відчинено!")
    elif scenario == "smoke":
        DEVICES['smoke_detector']['value'] = "ON"
        payload = {"value": "ON", "ts": ts}
        clients["smoke_detector"].publish(f"{DEVICES['smoke_detector']['topic']}/telemetry", json.dumps(payload))
    elif scenario == "motion":
        DEVICES['motion_yard']['value'] = "ON"
        payload = {"value": "ON", "ts": ts}
        clients["motion_yard"].publish(f"{DEVICES['motion_yard']['topic']}/telemetry", json.dumps(payload))
    elif scenario == "pin":
        DEVICES['keypad']['value'] = "1234"
        payload = {"value": "1234", "ts": ts}
        clients["keypad"].publish(f"{DEVICES['keypad']['topic']}/telemetry", json.dumps(payload))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=str, choices=["smoke", "break_in", "motion", "pin", "none"], default="none")
    args = parser.parse_args()
    setup_clients()
    time.sleep(1)
    try:
        if args.scenario != "none":
            run_scenario(args.scenario)
        while True:
            ts = int(time.time())
            for dev_id, client in clients.items():
                if DEVICES[dev_id]["type"] == "sensor" and dev_id != "keypad":
                    payload = {"value": DEVICES[dev_id]["value"], "ts": ts}
                    client.publish(f"{DEVICES[dev_id]['topic']}/telemetry", json.dumps(payload))
            time.sleep(15)
    except KeyboardInterrupt:
        for dev_id, client in clients.items():
            client.publish(f"{DEVICES[dev_id]['topic']}/status", "offline", retain=True)
            client.disconnect()
            client.loop_stop()