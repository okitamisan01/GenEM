# GenEM × Toyota HSR × ROS 2 Jazzy

自然言語 → 構造化行動 → 検証 → Skill API → Mock の研究用プロトタイプです。
Ubuntu 24.04 / Python 3.12 / ROS 2 Jazzy を独立したDocker構成で提供します。
**HSR実機の制御は未実装・無効です。** `--hsr` は常に終了コード2で拒否します。

[GenEM原研究](https://generative-expressive-motion.github.io/)を参考にした独自実装です。
原著者のコード・実験結果の再現を主張しません。
[研究調査](docs/genem_research.md)と[差分・制約](docs/limitations.md)を参照してください。
デフォルトの `offline` は5シナリオ用のルールベースで、LLMではありません。

## 構成

```text
Instruction + previous behavior + feedback
        ↓
OfflineGenerator / APIBehaviorGenerator (replaceable)
        ↓ JSON/YAML
Strict parser + bounds/duration validator
        ↓ (execution revalidates the whole plan)
BehaviorExecutor → RobotSkillInterface
                         ├─ Mock: ordered event log
                         └─ HSR: disabled integration scaffold
```

`genem_hsr` に生成・検証・実行・履歴・Skill APIを、`genem_demo` にCLIを配置しています。
ROSの `ament_python` パッケージですが、Mock処理自体はROS通信を必要としません。
詳細は[アーキテクチャ](docs/architecture.md)。

## Dockerで構築・実行

Linux上のDocker EngineとCompose v2が必要です。ホストへのROSインストールは不要です。

```bash
git clone --branch feature/genem-prototype https://github.com/okitamisan01/GenEM.git
cd GenEM
bash docker/build.sh
bash docker/up.sh
bash docker/exec.sh
```

コンテナ内で:

```bash
cd ~/colcon_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
ros2 run genem_demo interactive_demo --mock
```

指示例: `hello` または `Acknowledge the person.`。`hello` / `hi` / `hey` は注視とうなずきに変換します。
未対応の入力は例を表示して再入力を促します。`quit` / `exit` で終了できます。
表示された行動を `y` でMock実行し、
`Make it slower and friendlier.` で修正できます。空のフィードバックで終了します。
ROS通信範囲は初期状態ではLOCALHOST、CPUのみです。
[Docker詳細・GPU・ネットワーク](docs/docker_setup.md)を参照してください。

## 5つのデモ

```bash
ros2 run genem_demo interactive_demo --mock --scenario nod --yes
ros2 run genem_demo interactive_demo --mock --scenario shake_head --yes
ros2 run genem_demo interactive_demo --mock --scenario become_attentive --yes
ros2 run genem_demo interactive_demo --mock --scenario acknowledge_person --yes
ros2 run genem_demo interactive_demo --mock --scenario pay_attention_to_person --yes
ros2 run genem_demo interactive_demo --mock --scenario acknowledge_person \
  --feedback 'Make it slower and friendlier.' --yes
```

`--yes` はMockの確認省略のみです。`--hsr` を有効化しません。
Mockは関節を動かさず、待機や音声・人物注視もイベント記録のみです。
入力ファイル例は `demos/*.json`。`--behavior-file /path/to/behavior.json` で読み込めます。
コンテナの履歴 `~/genem_logs/history.jsonl` はホストの `logs/` に保存され、Git対象外です。

## LLM API

`APIBehaviorGenerator` は汎用のchat-completions形式に対応します。
ベンダーSDKには依存しません。別形式のAPIは `BehaviorGenerator` の実装を追加してください。

```bash
cp docker/env.example docker/.env
# docker/.env の GENEM_API_BASE / GENEM_MODEL / GENEM_API_KEY を編集
bash docker/up.sh --force-recreate
bash docker/exec.sh
# コンテナ内:
ros2 run genem_demo interactive_demo --mock --backend api \
  --instruction 'Politely acknowledge a person.'
```

`GENEM_API_BASE` は `/v1` などを含むベースURLです。`/chat/completions` を付加します。
HTTPSを利用し、ローカル開発用ループバックに限りHTTPを許可します。
APIキーは環境変数からのみ読み込みます。プロンプト・履歴には保存しません。
実APIとの通信は未検証です。APIテストは偽の通信・偽のキーを使います。

## テスト

コンテナ内:

```bash
cd ~/colcon_ws
colcon build --symlink-install
source install/setup.bash
colcon test --event-handlers console_direct+
colcon test-result --verbose
```

ホストのPythonで試す場合（ROS不要）:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -q
PYTHONPATH=ros2_ws/src/genem_hsr:ros2_ws/src/genem_demo \
  python -m genem_demo.cli --mock --scenario nod --yes
```

検証結果と実行条件は[検証記録](docs/validation.md)。

## HSR接続

[HSR統合調査とTODO](docs/hsr_integration.md)に既存ROS 2コードの根拠を記載しています。
実機のROS世代、名前空間、制限値、現在姿勢、停止処理、監督と非常停止手段の確認が必要です。
この版はロボット用Publisher/Action Clientを作成せず、動作命令を送りません。
Mockの角度・速度制限は実機の安全性を保証しません。

## 移植・既知の制約・今後

Docker構築はGenEM内のファイルのみで完結します。`docker_ws` は実行時依存ではありません。

```bash
docker save -o genem_hsr.tar genem-hsr:jazzy
docker load -i genem_hsr.tar
```

tarやAPIキーをCommitしないでください。ネットワークなしの移植には同じCPUアーキテクチャの
保存済みイメージを使えます。初回ビルドには外部レジストリとapt/rosdepへの接続が必要です。
ベースイメージはdigest固定ですが、apt依存の完全なバイト一致は保証しません。

未実装: 実機制御・人物検出追跡・音声合成・台車制御・学習済みSkillの自動追加・
原論文の複数段階推論とフィードバック振り分け・人による表出性評価。
今後は検証済みHSRプロファイル、シミュレーター、長期HRIと個人化を追加します。
[英語ミーティング資料](docs/implementation_summary.md)も用意しています。

開発・Push先は `okitamisan01/GenEM` の `feature/genem-prototype` のみです。
`main` へのMergeは行いません。ライセンスは[BSD-3-Clause](LICENSE)、
参考元の扱いは[Third-party notices](docs/third_party_notices.md)を参照してください。
