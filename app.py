import os
import sqlite3
import hashlib
import secrets
from datetime import datetime, date
from io import BytesIO

import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "fortune_ai.db")
APP_TITLE = "FORTUNE AI"

st.set_page_config(page_title=APP_TITLE, page_icon="🔮", layout="centered")

# --- Database ---
def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            birthday TEXT,
            category TEXT NOT NULL,
            question TEXT NOT NULL,
            method TEXT NOT NULL,
            reading TEXT NOT NULL
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )""")

def save_reading(customer_name, birthday, category, question, method, reading):
    with db() as con:
        con.execute(
            """INSERT INTO readings
            (created_at, customer_name, birthday, category, question, method, reading)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (datetime.now().isoformat(timespec="minutes"), customer_name, birthday,
             category, question, method, reading)
        )

def get_readings():
    with db() as con:
        return con.execute("SELECT * FROM readings ORDER BY id DESC").fetchall()

def get_setting(key, default=""):
    with db() as con:
        row = con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

def set_setting(key, value):
    with db() as con:
        con.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, value))

init_db()

# --- Fortune logic: entertainment / self-reflection, not deterministic claims ---
NUMBER_TEXT = {
    1: "自立・行動力。自分で決めた小さな一歩を形にすることがテーマです。",
    2: "協調・調整力。相手の立場を理解しながら、自分の希望も大切にしましょう。",
    3: "表現・好奇心。楽しみながら試すことが、新しい発見につながりそうです。",
    4: "継続・安定。計画を小さく分け、無理のないペースで積み上げましょう。",
    5: "柔軟性・変化。新しい経験を取り入れつつ、自分の軸を確認するとよさそうです。",
    6: "思いやり・責任感。人を支えることと、自分をいたわることの両方を意識しましょう。",
    7: "探究・分析。じっくり学ぶ時間が、自分ならではの強みを育ててくれそうです。",
    8: "実行・達成。目標を具体的な数字や期限に落とし込むことがヒントです。",
    9: "共感・広い視野。これまでの経験を振り返り、誰かの役に立つ形を考えてみましょう。",
    11: "直感・ひらめき。思いつきを記録し、実行できる小さな行動に変えてみましょう。",
    22: "構想・実現。大きな目標を段階に分け、着実に進めることを意識しましょう。",
    33: "包容力・創造性。人への優しさと、自分の負担を増やしすぎない境界線がテーマです。",
}
TAROT = [
    ("愚者", "新しい可能性・自由な発想", "完璧を待つより、小さく試して学ぶ姿勢が次の選択肢を広げそうです。"),
    ("魔術師", "才能・準備・スタート", "今ある経験や道具を見直し、できることから具体的な行動に移してみましょう。"),
    ("女教皇", "冷静さ・観察・内省", "急いで答えを出さず、情報と自分の本音を整理する時間を持つとよさそうです。"),
    ("女帝", "豊かさ・育成・思いやり", "人との関係や日々の積み重ねを大切に。自分にも余裕を与えてみましょう。"),
    ("皇帝", "計画・責任・安定", "優先順位や期限を明確にすると、目標に向けて進みやすくなりそうです。"),
    ("恋人", "選択・調和・価値観", "周囲の期待だけでなく、自分が大切にしたい価値観を確かめてみましょう。"),
    ("戦車", "集中・前進・挑戦", "やることを絞って集中を。途中で方向を確認する余白も忘れずに。"),
    ("力", "粘り強さ・自制・優しさ", "無理に押し切るより、落ち着いて向き合うことが力になりそうです。"),
    ("隠者", "探究・専門性・内省", "一人で考えたり学んだりする時間が、自分なりの答えにつながるかもしれません。"),
    ("運命の輪", "変化・転機・タイミング", "状況の変化をすぐに判断せず、活用できる機会がないか探してみましょう。"),
    ("正義", "公平・判断・バランス", "事実と気持ちを分けて整理し、条件を確認してから選ぶことがヒントです。"),
    ("星", "希望・展望・回復", "目指したい方向を思い出し、実現に向けた小さな習慣を始めてみましょう。"),
]
CATEGORY_ADVICE = {
    "恋愛": "相手の気持ちを決めつけず、自分の希望を穏やかに伝えることを意識してみましょう。",
    "仕事": "強み・改善点・次に伸ばしたい能力を一つずつ言葉にすると、行動が見えやすくなります。",
    "金運": "固定費や支出を見直し、数字とリスクを確認して判断することが現実的な一歩です。",
    "総合": "睡眠・時間の使い方・人間関係など、生活の土台を一つ整えてみましょう。",
    "人間関係": "相手に合わせすぎず、自分が心地よくいられる距離感や伝え方を探してみましょう。",
}

def life_path(bday):
    n = sum(int(x) for x in bday.strftime("%Y%m%d"))
    while n > 9 and n not in (11, 22, 33):
        n = sum(int(x) for x in str(n))
    return n

def local_reading(name, bday, category, question, method):
    import random
    n = life_path(bday)
    card, keywords, card_text = random.choice(TAROT)
    return f"""【{name}さんの鑑定】

■ ご相談テーマ：{category}
■ 生年月日：{bday.strftime('%Y年%m月%d日')}
■ 鑑定方法：{method}

【数秘術：{n}】
{NUMBER_TEXT[n]}

【タロット：{card}】
キーワード：{keywords}
{card_text}

【今回のアドバイス】
{CATEGORY_ADVICE[category]}

【ご相談内容】
{question}

この鑑定は、いただいた内容を振り返り、自分の考えを整理するための一つの視点です。
結果を断定するものではありません。大切な判断は、ご自身の状況や信頼できる情報も踏まえて行ってください。"""

def ai_reading(name, bday, category, question, method, api_key):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        prompt = f"""あなたは、娯楽と自己理解を目的とする占いサービスの鑑定文ライターです。
断定、恐怖をあおる表現、依存を促す表現、医療・法律・投資の助言を避けてください。
相談者が前向きに考えを整理できる、丁寧で具体的な日本語の鑑定文を作成してください。
占術の結果を事実や未来の保証として扱わず、行動のヒントとして表現してください。
名前：{name}
生年月日：{bday}
テーマ：{category}
鑑定方法：{method}
相談内容：{question}
見出しを付け、800〜1200字程度で作成してください。"""
        response = client.responses.create(model="gpt-4.1-mini", input=prompt)
        return response.output_text
    except Exception as e:
        return None, str(e)

def make_pdf(customer_name, content):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
    c.setFont("HeiseiKakuGo-W5", 16)
    c.drawString(48, 800, "FORTUNE AI 鑑定レポート")
    c.setFont("HeiseiKakuGo-W5", 9)
    c.drawString(48, 780, f"お客様：{customer_name}")
    y = 750
    c.setFont("HeiseiKakuGo-W5", 10)
    for line in content.splitlines():
        if y < 55:
            c.showPage()
            c.setFont("HeiseiKakuGo-W5", 10)
            y = 800
        # simple wrapping by Japanese character count
        chunks = [line[i:i+48] for i in range(0, max(len(line), 1), 48)]
        for chunk in chunks:
            c.drawString(48, y, chunk)
            y -= 16
    c.save()
    buffer.seek(0)
    return buffer

# --- UI ---
st.markdown("""
<style>
.stApp {background: linear-gradient(180deg, #17112b 0%, #21183a 38%, #101522 100%); color:#f8f4ff;}
h1,h2,h3,p,label {color:#f8f4ff !important;}
div[data-testid="stForm"] {background:rgba(255,255,255,.05); padding:18px; border:1px solid rgba(222,196,255,.22); border-radius:18px;}
div.stButton > button, div.stFormSubmitButton > button {border-radius:12px; font-weight:700;}
.small-note {color:#c8bddb;font-size:12px;}
</style>
""", unsafe_allow_html=True)

st.title("🔮 FORTUNE AI")
st.caption("占い師のための鑑定・顧客管理ワークスペース")
st.warning("MVP試作品です。現段階ではデモ用途です。顧客情報を実際に集める前に、認証・暗号化・バックアップ・プライバシーポリシー等の整備が必要です。")

tab_customer, tab_admin, tab_settings = st.tabs(["✨ 鑑定を作る", "📚 鑑定履歴", "⚙️ 設定"])

with tab_customer:
    st.subheader("新しい鑑定")
    with st.form("new_reading"):
        customer = st.text_input("お客様のお名前・ニックネーム", placeholder="例：さくら")
        bday = st.date_input("生年月日", value=date(1998, 6, 15), min_value=date(1900,1,1), max_value=date.today())
        category = st.selectbox("相談テーマ", list(CATEGORY_ADVICE.keys()))
        method = st.selectbox("鑑定スタイル", ["数秘術＋タロット", "数秘術", "タロット", "オリジナル総合鑑定"])
        question = st.text_area("相談内容", placeholder="相談者の悩みや知りたいことを入力してください。")
        submitted = st.form_submit_button("鑑定文を作成する", use_container_width=True)

    if submitted:
        if not customer.strip() or not question.strip():
            st.error("お名前と相談内容を入力してください。")
        else:
            key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
            use_ai = bool(key)
            if use_ai:
                result = ai_reading(customer.strip(), bday, category, question.strip(), method, key)
                if isinstance(result, tuple):
                    st.warning("AI APIに接続できなかったため、基本鑑定で作成しました。設定やAPI利用状況を確認してください。")
                    result = local_reading(customer.strip(), bday, category, question.strip(), method)
            else:
                result = local_reading(customer.strip(), bday, category, question.strip(), method)
                st.info("AI APIキー未設定のため、内蔵テンプレートで鑑定文を作成しました。AIによる文章生成を使う場合は設定タブを確認してください。")
            save_reading(customer.strip(), bday.isoformat(), category, question.strip(), method, result)
            st.session_state["latest_reading"] = result
            st.session_state["latest_customer"] = customer.strip()

    if st.session_state.get("latest_reading"):
        st.divider()
        st.subheader("鑑定結果")
        st.text_area("編集可能な鑑定文", value=st.session_state["latest_reading"], height=360, key="editable_result")
        if st.button("編集内容をPDFにする"):
            pdf = make_pdf(st.session_state.get("latest_customer", "お客様"), st.session_state["editable_result"])
            st.download_button("PDFをダウンロード", data=pdf, file_name="fortune_report.pdf", mime="application/pdf")

with tab_admin:
    st.subheader("鑑定履歴・簡易管理")
    rows = get_readings()
    st.metric("保存済み鑑定数", len(rows))
    if rows:
        for row in rows[:30]:
            with st.expander(f"#{row['id']}｜{row['customer_name']}｜{row['category']}｜{row['created_at'][:16]}"):
                st.write("**相談内容**")
                st.write(row["question"])
                st.write("**鑑定文**")
                st.write(row["reading"])
    else:
        st.info("まだ鑑定履歴はありません。")

with tab_settings:
    st.subheader("サービス設定")
    st.write("AI文章生成を有効にするには、OpenAI APIキーを設定します。API利用料が別途発生します。")
    st.code('OPENAI_API_KEY = "sk-..."', language="toml")
    st.caption("Streamlit Community Cloudでは、アプリの Settings → Secrets に設定してください。APIキーをコードや公開リポジトリに書かないでください。")
    st.markdown("**将来の有料プラン例（価格は仮案）**")
    st.table([
        {"プラン": "Starter", "月額": "¥980", "想定機能": "月30件まで"},
        {"プラン": "Pro", "月額": "¥2,980", "想定機能": "月200件・PDF出力"},
        {"プラン": "Studio", "月額": "¥5,980", "想定機能": "複数鑑定師・顧客管理"},
    ])
    st.caption("料金・件数は事業検討用の仮設定であり、決済・利用制限はまだ実装されていません。")

st.divider()
st.caption("FORTUNE AI MVP v0.1｜占いは娯楽・自己理解のための参考情報です。未来を保証するものではありません。")
