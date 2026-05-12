import os
import json
import smbclient
import smbprotocol.exceptions
from google.cloud import pubsub_v1
import logging
import traceback

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/etc/gcp/serviceAccountKey.json"
SUBSCRIPTION_PATH = os.getenv("SUBSCRIPTION_PATH")
SERVER = os.getenv("SMB_SERVER")
USERNAME = os.getenv("SMB_USERNAME")
PASSWORD = os.getenv("SMB_PASSWORD")
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

# セッションの登録（起動時に一度だけ行う）
try:
    smbclient.register_session(SERVER, username=USERNAME, password=PASSWORD)
    logger.info(f"SMBセッションを登録しました: {SERVER}")
except Exception as e:
    logger.error(f"SMBセッションの登録に失敗しました: {e}")
    # 初期化失敗は致命的なので再試行せず終了
    exit(1)

def callback(message):
    try:
        data = json.loads(message.data.decode('utf-8'))
        action = data.get("action")
        file_path = data.get("file_path") or data.get("old_path")
        logger.info(f"処理開始: action={action}, path={file_path}")

        if action == "delete":
            file_path = data.get("file_path")
            if not DRY_RUN:
                try:
                    smbclient.remove(file_path)
                    logger.info(f"削除成功: {file_path}")
                except smbprotocol.exceptions.SMBOSError as e:
                    # NtStatus 0xc0000033 (Name invalid), 0xc0000034 (Name not found), 0xc000003a (Path not found)
                    if e.ntstatus in [0xc0000033, 0xc0000034, 0xc000003a]:
                        logger.warning(f"対象が無効または見つかりません（スキップ）: {file_path} (Status: {hex(e.ntstatus)})")
                    else:
                        raise
            else:
                logger.info(f"削除 (DRY_RUN): {file_path}")

        elif action == "rename":
            old_path = data.get("old_path")
            new_path = data.get("new_path")

            if not DRY_RUN:
                # 親ディレクトリの存在確認と作成
                if "/" in new_path:
                    parent = new_path.rsplit('/', 1)[0]
                    try:
                        smbclient.stat(parent)
                    except Exception:
                        try:
                            smbclient.makedirs(parent, exist_ok=True)
                            logger.info(f"ディレクトリ作成: {parent}")
                        except Exception as e:
                            logger.warning(f"ディレクトリ作成に失敗しました (無視して進めます): {e}")

                try:
                    smbclient.rename(old_path, new_path)
                    logger.info(f"移動成功: {old_path} -> {new_path}")
                except smbprotocol.exceptions.SMBOSError as e:
                    if e.ntstatus in [0xc0000033, 0xc0000034, 0xc000003a]:
                        logger.warning(f"移動元が無効または見つかりません（スキップ）: {old_path} (Status: {hex(e.ntstatus)})")
                    else:
                        raise
            else:
                logger.info(f"移動 (DRY_RUN): {old_path} -> {new_path}")

        message.ack()
    except Exception as e:
        logger.error(f"メッセージ処理中にエラーが発生しました: {e}")
        logger.debug(traceback.format_exc())
        # 致命的なエラーでない限りはnackしてリトライさせる
        # ただし、特定の致命的なSMBエラーなどの場合は終了を検討する
        message.nack()

subscriber = pubsub_v1.SubscriberClient()
streaming_pull_future = subscriber.subscribe(SUBSCRIPTION_PATH, callback=callback)

if DRY_RUN:
    logger.info(f"DRY_RUNモードで監視を開始しました: {SUBSCRIPTION_PATH}")
else:
    logger.info(f"監視を開始しました: {SUBSCRIPTION_PATH}")

with subscriber:
    try:
        # 結果を待機（エラーが発生すると例外がスローされる）
        streaming_pull_future.result()
    except KeyboardInterrupt:
        logger.info("ユーザーにより停止されました")
        streaming_pull_future.cancel()
    except Exception as e:
        logger.error(f"サブスクライバーで致命的なエラーが発生しました: {e}")
        logger.error(traceback.format_exc())
        streaming_pull_future.cancel()
        # コンテナを再起動させるために異常終了させる
        exit(1)
