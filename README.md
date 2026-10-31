# FORTUNE AI MVP

占い師向けAI鑑定ワークスペースの初期試作品です。iPhoneのブラウザからも、公開後のURLにアクセスして利用できます。

## できること
- 相談者名、生年月日、相談テーマ、相談内容の入力
- 内蔵テンプレートによる数秘術＋タロット風の鑑定文作成
- OpenAI APIキーを設定した場合のAI鑑定文生成（API料金別途）
- 鑑定履歴のSQLite保存
- 鑑定文の編集
- PDFレポート出力

## iPhoneだけで公開する手順（Streamlit Community Cloud）
1. GitHubアカウントを作成・ログイン
2. GitHubで新しいPublicまたはPrivateリポジトリを作成
3. `app.py` と `requirements.txt` をアップロード
4. https://share.streamlit.io/ を開き、GitHubで接続
5. New app → リポジトリ → `app.py` を選択してDeploy
6. AI生成を使う場合、アプリのSettings → Secretsに次を設定

```toml
OPENAI_API_KEY = "あなたのAPIキー"
```

APIキーは公開コードに書かないでください。

## 注意
これはMVP（試作品）であり、他の占い師へ有料提供できる完成SaaSではありません。
現在のSQLite保存は単一アプリ環境向けの簡易実装です。複数ユーザーの本番利用には、ユーザー認証、テナントごとのデータ分離、クラウドDB、暗号化、バックアップ、決済、利用制限、監査ログ、プライバシーポリシー、利用規約などが必要です。
実在の顧客の氏名・生年月日・相談内容を入れる前に、適切な安全対策を実装してください。
