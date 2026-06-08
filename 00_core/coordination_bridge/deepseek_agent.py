import os, time, json, glob, datetime

INCOMING_DIR = r'E:\\Jericho\\coordination_bridge\\incoming'
RESULTS_DIR = r'E:\\Jericho\\coordination_bridge\\results'
HEARTBEAT_INTERVAL = 60  # seconds

def heartbeat():
    while True:
        try:
            hb = {
                'agent': 'DeepSeek (background)',
                'timestamp': datetime.datetime.now().isoformat(),
                'status': 'active',
                'via': 'V4Lite spawned'
            }
            hb_file = os.path.join(RESULTS_DIR, f"deepseek_hb_{int(time.time())}.json")
            with open(hb_file, 'w', encoding='utf-8') as f:
                json.dump(hb, f, indent=2)
            # clean old heartbeats (keep last 50)
            all_hb = sorted(glob.glob(os.path.join(RESULTS_DIR, 'deepseek_hb_*.json')))
            for old in all_hb[:-50]:
                os.remove(old)
        except Exception as e:
            print(f'Heartbeat error: {e}')
        time.sleep(HEARTBEAT_INTERVAL)

def monitor_incoming():
    processed = set()
    while True:
        try:
            for fname in os.listdir(INCOMING_DIR):
                if fname.endswith('.txt') and fname not in processed:
                    path = os.path.join(INCOMING_DIR, fname)
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    # Если сообщение содержит ключ 'DeepSeek' или '4 февраля' или обращение к нам
                    if 'DeepSeek' in content or '4 февраля' in content or 'deepseek' in content.lower():
                        signal_file = os.path.join(RESULTS_DIR, 'new_message_for_DeepSeek.sig')
                        with open(signal_file, 'w', encoding='utf-8') as sig:
                            sig.write(f'{datetime.datetime.now().isoformat()} - {fname}:\n{content[:500]}')
                    processed.add(fname)
        except Exception as e:
            print(f'Monitor error: {e}')
        time.sleep(15)

if __name__ == '__main__':
    import threading
    threading.Thread(target=heartbeat, daemon=True).start()
    threading.Thread(target=monitor_incoming, daemon=True).start()
    # Keep alive
    while True:
        time.sleep(1)
