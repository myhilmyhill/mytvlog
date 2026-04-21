import os
import json
import smbclient
from google.cloud import pubsub_v1

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/etc/gcp/serviceAccountKey.json"
SUBSCRIPTION_PATH = os.getenv("SUBSCRIPTION_PATH")
SERVER = os.getenv("SMB_SERVER")
USERNAME = os.getenv("SMB_USERNAME")
PASSWORD = os.getenv("SMB_PASSWORD")
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
subscriber = pubsub_v1.SubscriberClient()

def callback(message):
    data = json.loads(message.data.decode('utf-8'))
    action = data.get("action")

    # セッションの登録（既存のものがあれば上書き）
    smbclient.register_session(SERVER, username=USERNAME, password=PASSWORD)

    if action == "delete":
        file_path = data.get("file_path")
        if not DRY_RUN:
            smbclient.remove(file_path)
        print(f"削除: {file_path}")

    elif action == "rename":
        old_path = data.get("old_path")
        new_path = data.get("new_path")

        # 親ディレクトリが存在することを確認
        parent = "/".join(new_path.split("/")[:-1])
        if not DRY_RUN:
            try:
                smbclient.stat(parent)
            except Exception:
                smbclient.makedirs(parent, exist_ok=True)
                print(f"ディレクトリ作成: {parent}")

        print(f"移動: {old_path} -> {new_path}")
        if not DRY_RUN:
            smbclient.rename(old_path, new_path)

    message.ack()

streaming_pull_future = subscriber.subscribe(SUBSCRIPTION_PATH, callback=callback)
if DRY_RUN:
    print(f"DRY_RUNモードで監視を開始しました: {SUBSCRIPTION_PATH}")
else:
    print(f"監視を開始しました: {SUBSCRIPTION_PATH}")

with subscriber:
    try:
        streaming_pull_future.result()
    except KeyboardInterrupt:
        streaming_pull_future.cancel()
