
## 共通セットアップ
認証をGitHub Appでする。作ってenvに登録する。GITHUB_CLIENT_ID、GITHUB_CLIENT_SECRET

定期的に視聴してる番組情報を取得して登録してくれる。.envに現在情報を取得するAPIのアドレスを入れて、pollをローカルで起動する

PubSubでファイルの操作とかをリモートでする。.envにPUBSUB系の設定を設定して、IAMにPub/Sub Subscriberを付与したサービスアカウントのkeyをpubsub-smb-controllerにserviceAccountKey.jsonを置く。.envにSMBの情報などを入れる。pubsub-smb-controllerをローカルで起動する

GitHub ModelでLLMがシリーズ名を抜き出してくれる。PAT発行してGITHUB_TOKENに入れる

mytvrecommenderはMCPサーバーとして起動する。番組表を取得するには.envにEDCBのアドレスを入れる

EDCBのPostRecなどで録画情報を登録する感じのをtestapiで実行する。.envは録画情報の取得にEDCB、ファイルサイズの取得にSMB、ログインにGitHubを入れる

## ローカルで動かすとき
DB=sqlite として起動する。起動時に勝手にDBが作られる。

Pub/Sub Publisher、BigQuery Data EditorをIAMで付与する

## Cloud Runで動かすとき
DB=bigquery として起動する。
その前に db/bigquery/schemas.sql を適当なbqコマンドで実行してDBを作る。
環境変数でbigquery_project_id、bigquery_dataset_idを設定する。
