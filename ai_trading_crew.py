import time
from datetime import datetime, timezone

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# AI Trading Crew — educational Solana market scanner + paper portfolio.
# Data: public DexScreener market endpoints. No wallet connection or real orders.

st.set_page_config(page_title="AI Trading Crew | Solana", page_icon="🤖", layout="wide")

st.markdown("""
<style>
.stApp {background: #0b1020; color: #e8edf8;}
[data-testid="stMetric"] {background:#131b2f; border:1px solid #26334f; padding:14px; border-radius:12px;}
div[data-testid="stDataFrame"] {border:1px solid #26334f; border-radius:10px;}
section[data-testid="stSidebar"] {background:#10182a;}
.block-container {padding-top:1.4rem; max-width:1500px;}
.small-muted {color:#93a4c4;font-size:0.86rem;}
.agent-card {background:#131b2f;border:1px solid #26334f;border-radius:12px;padding:14px;min-height:150px;}
.agent-name {font-size:1.05rem;font-weight:700;color:#f3f6ff;}
.agent-score {font-size:1.8rem;font-weight:800;color:#80e0bd;}
</style>
""", unsafe_allow_html=True)

API = "https://api.dexscreener.com/latest/dex/search"

@st.cache_data(ttl=30, show_spinner=False)
def get_market_data():
    queries = ["SOL", "BONK", "WIF", "JUP", "RAY", "POPCAT", "PYTH", "MEW"]
    rows = []
    errors = []
    for query in queries:
        try:
            r = requests.get(API, params={"q": query}, timeout=12,
                             headers={"User-Agent": "AI-Trading-Crew-Educational/1.0"})
            r.raise_for_status()
            for p in (r.json().get("pairs") or []):
                if p.get("chainId") != "solana":
                    continue
                token = p.get("baseToken") or {}
                liq = (p.get("liquidity") or {}).get("usd") or 0
                if not token.get("address"):
                    continue
                rows.append({
                    "name": token.get("name", "Unknown"),
                    "symbol": token.get("symbol", "?"),
                    "address": token.get("address"),
                    "pair": p.get("pairAddress", ""),
                    "dex": p.get("dexId", "—"),
                    "url": p.get("url", ""),
                    "price": safe_float(p.get("priceUsd")),
                    "change5m": safe_float((p.get("priceChange") or {}).get("m5")),
                    "change1h": safe_float((p.get("priceChange") or {}).get("h1")),
                    "change6h": safe_float((p.get("priceChange") or {}).get("h6")),
                    "change24h": safe_float((p.get("priceChange") or {}).get("h24")),
                    "volume24": safe_float((p.get("volume") or {}).get("h24")),
                    "volume1h": safe_float((p.get("volume") or {}).get("h1")),
                    "liquidity": safe_float(liq),
                    "buys1h": safe_float(((p.get("txns") or {}).get("h1") or {}).get("buys")),
                    "sells1h": safe_float(((p.get("txns") or {}).get("h1") or {}).get("sells")),
                    "buys24h": safe_float(((p.get("txns") or {}).get("h24") or {}).get("buys")),
                    "sells24h": safe_float(((p.get("txns") or {}).get("h24") or {}).get("sells")),
                    "fdv": safe_float(p.get("fdv")),
                    "created": p.get("pairCreatedAt"),
                })
        except Exception as e:
            errors.append(f"{query}: {e}")
    if not rows:
        return pd.DataFrame(), errors
    df = pd.DataFrame(rows)
    # Keep the most liquid pool for each token, avoiding duplicate pools in the main board.
    df = df.sort_values("liquidity", ascending=False).drop_duplicates("address")
    return df.reset_index(drop=True), errors


def safe_float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def age_hours(timestamp_ms):
    if not timestamp_ms:
        return None
    return max(0.0, (time.time() - float(timestamp_ms) / 1000) / 3600)


def clamp(x, low=0, high=100):
    return max(low, min(high, x))


def analyze(row):
    h1 = row["change1h"]
    h24 = row["change24h"]
    m5 = row["change5m"]
    vol = row["volume24"]
    liq = row["liquidity"]
    buys = row["buys1h"]
    sells = row["sells1h"]
    tx = buys + sells
    buy_ratio = buys / tx if tx else 0.5
    age = age_hours(row["created"])

    # Five transparent heuristic agents. Scores are educational indicators, not predictions.
    sniper = clamp(45 + (18 if age is not None and age < 24 else 0)
                   + min(liq / 5000, 18) + min(vol / 10000, 15)
                   - (20 if liq < 5000 else 0))
    momentum = clamp(50 + h1 * 1.3 + h24 * 0.22 + (buy_ratio - 0.5) * 35)
    dip = clamp(48 + max(0, -h24) * 0.65 + (buy_ratio - 0.5) * 45
                - max(0, -h1) * 0.8)
    flow = clamp(45 + (buy_ratio - 0.5) * 55
                 + min(tx / 20, 20) + min(vol / max(liq, 1) * 12, 15))
    scalper = clamp(50 + m5 * 2.2 + h1 * 0.9 + (buy_ratio - 0.5) * 30)
    scores = {
        "Sniper": sniper, "Momentum": momentum, "Dip Hunter": dip,
        "Whale Tail*": flow, "Scalper": scalper
    }
    consensus = sum(scores.values()) / len(scores)
    risk = []
    if liq < 10000:
        risk.append("Likuiditas tipis")
    if vol > 0 and liq > 0 and vol / liq > 8:
        risk.append("Volume/liquiditas ekstrem")
    if tx < 10:
        risk.append("Aktivitas transaksi rendah")
    if age is not None and age < 2:
        risk.append("Pool sangat baru")
    if abs(h24) > 80:
        risk.append("Perubahan 24 jam ekstrem")
    return scores, consensus, risk, buy_ratio, age


def money(v):
    if v >= 1_000_000:
        return f"${v/1_000_000:.2f}M"
    if v >= 1_000:
        return f"${v/1_000:.1f}K"
    return f"${v:,.2f}"


if "cash" not in st.session_state:
    st.session_state.cash = 1000.0
if "positions" not in st.session_state:
    st.session_state.positions = {}
if "trades" not in st.session_state:
    st.session_state.trades = []

st.title("🤖 AI TRADING CREW")
st.caption("SOLANA MARKET INTELLIGENCE • ADVANCED PAPER-TRADING LAB")
st.warning("MODE SIMULASI — Tidak ada wallet, private key, atau transaksi uang sungguhan. Skor agen adalah heuristik edukatif, bukan saran investasi atau jaminan hasil.")

with st.sidebar:
    st.header("⚙️ Control Center")
    refresh = st.slider("Refresh interval (detik)", 30, 300, 60, 15)
    min_liq = st.number_input("Filter likuiditas minimum (USD)", min_value=0, value=5000, step=1000)
    min_score = st.slider("Ambang skor konsensus", 0, 100, 60)
    st.divider()
    st.subheader("Paper wallet")
    st.metric("Saldo kas simulasi", f"${st.session_state.cash:,.2f}")
    st.caption("Modal awal: $1,000 simulasi")
    if st.button("Reset simulasi", use_container_width=True):
        st.session_state.cash = 1000.0
        st.session_state.positions = {}
        st.session_state.trades = []
        st.rerun()
    st.divider()
    st.caption("Sumber data: DexScreener public API. Refresh manual/otomatis melalui tombol di bawah.")

col_a, col_b = st.columns([1, 5])
with col_a:
    if st.button("↻ Refresh data", use_container_width=True):
        get_market_data.clear()
        st.rerun()
with col_b:
    st.markdown(f"<div class='small-muted'>Pembaruan terakhir saat data dimuat • interval pilihan {refresh} detik (gunakan tombol refresh untuk memuat ulang)</div>", unsafe_allow_html=True)

with st.spinner("Mengambil pasangan pasar Solana..."):
    df, errors = get_market_data()

if df.empty:
    st.error("Data pasar belum berhasil dimuat. Periksa koneksi internet, lalu tekan Refresh data.")
    if errors:
        st.code("\n".join(errors[:3]))
    st.stop()

analyses = df.apply(analyze, axis=1)
df["agents"] = analyses.apply(lambda x: x[0])
df["score"] = analyses.apply(lambda x: x[1])
df["risks"] = analyses.apply(lambda x: x[2])
df["buy_ratio"] = analyses.apply(lambda x: x[3])
df["age_hours"] = analyses.apply(lambda x: x[4])
df["signal"] = df["score"].apply(lambda s: "WATCHLIST" if s >= min_score else "OBSERVE")
filtered = df[df["liquidity"] >= min_liq].sort_values("score", ascending=False).copy()

# Dashboard summary
total_tokens = len(filtered)
avg_score = filtered["score"].mean() if total_tokens else 0
high_activity = int((filtered["volume24"] > 100000).sum()) if total_tokens else 0
m1, m2, m3, m4 = st.columns(4)
m1.metric("Token/pool terpantau", total_tokens)
m2.metric("Rata-rata skor agen", f"{avg_score:.1f}/100")
m3.metric("Volume 24 jam terpantau", money(filtered["volume24"].sum()) if total_tokens else "$0")
m4.metric("Aktivitas volume tinggi", high_activity)

st.subheader("🧠 Lima agen analisis")
agent_cols = st.columns(5)
agent_info = [
    ("Sniper", "Mendeteksi pool baru + likuiditas"),
    ("Momentum", "Mengukur perubahan harga + volume"),
    ("Dip Hunter", "Mencari penurunan dan respons beli"),
    ("Whale Tail*", "Proxy arus transaksi; bukan pelacak wallet"),
    ("Scalper", "Membaca pergerakan jangka sangat pendek"),
]
if total_tokens:
    top_row = filtered.iloc[0]
    top_scores = top_row["agents"]
else:
    top_scores = {k: 0 for k, _ in agent_info}
for col, (name, desc) in zip(agent_cols, agent_info):
    score = top_scores.get(name, 0)
    col.markdown(f"<div class='agent-card'><div class='agent-name'>{name}</div><div class='agent-score'>{score:.0f}<span style='font-size:0.9rem'>/100</span></div><div class='small-muted'>{desc}</div></div>", unsafe_allow_html=True)

st.caption("*Whale Tail memakai rasio transaksi dan volume sebagai proksi aktivitas. API publik yang dipakai tidak mengidentifikasi transaksi wallet paus secara langsung.")

st.subheader("📡 Market scanner — Solana")
if filtered.empty:
    st.info("Tidak ada token yang memenuhi filter likuiditas. Turunkan filter di sidebar.")
else:
    display = filtered[["symbol", "name", "price", "change5m", "change1h", "change24h",
                        "volume24", "liquidity", "buy_ratio", "score", "signal"]].copy()
    display.columns = ["Ticker", "Nama", "Harga USD", "5m %", "1h %", "24h %",
                       "Volume 24h", "Likuiditas", "Rasio beli", "Skor AI", "Status"]
    st.dataframe(display, use_container_width=True, hide_index=True,
                 column_config={
                     "Harga USD": st.column_config.NumberColumn(format="$%.8f"),
                     "5m %": st.column_config.NumberColumn(format="%.2f%%"),
                     "1h %": st.column_config.NumberColumn(format="%.2f%%"),
                     "24h %": st.column_config.NumberColumn(format="%.2f%%"),
                     "Volume 24h": st.column_config.NumberColumn(format="$%.0f"),
                     "Likuiditas": st.column_config.NumberColumn(format="$%.0f"),
                     "Rasio beli": st.column_config.NumberColumn(format="%.0%%"),
                     "Skor AI": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f"),
                 })

left, right = st.columns([1.15, 0.85])
with left:
    st.subheader("📊 Peta risiko & momentum")
    if total_tokens:
        chart_df = filtered.head(35).copy()
        chart_df["Ukuran bubble"] = chart_df["volume24"].clip(lower=1)
        fig = px.scatter(chart_df, x="change24h", y="score", size="Ukuran bubble",
                         color="liquidity", hover_name="symbol",
                         hover_data={"name": True, "liquidity": ":,.0f", "volume24": ":,.0f",
                                     "score": ":.1f", "Ukuran bubble": False},
                         labels={"change24h": "Perubahan 24 jam (%)", "score": "Skor gabungan agen",
                                 "liquidity": "Likuiditas USD"},
                         color_continuous_scale="Teal")
        fig.update_layout(template="plotly_dark", paper_bgcolor="#0b1020",
                          plot_bgcolor="#0b1020", height=420, margin=dict(l=10,r=10,t=20,b=10))
        st.plotly_chart(fig, use_container_width=True)
with right:
    st.subheader("🚦 Daftar perhatian")
    if total_tokens:
        for _, r in filtered.head(6).iterrows():
            risk_text = ", ".join(r["risks"]) if r["risks"] else "Tidak ada flag dari filter sederhana"
            st.markdown(f"**{r['symbol']}** · Skor {r['score']:.0f}/100")
            st.caption(f"{r['signal']} | Risiko: {risk_text}")
            st.progress(int(r["score"]))

st.subheader("🔎 Analisis token terpilih")
if total_tokens:
    options = {f"{r['symbol']} — {r['name']}": r["address"] for _, r in filtered.iterrows()}
    selected_label = st.selectbox("Pilih token", list(options.keys()))
    selected = filtered[filtered["address"] == options[selected_label]].iloc[0]
    scores, consensus, risks, buy_ratio, age = analyze(selected)
    a, b, c, d = st.columns(4)
    a.metric("Skor konsensus", f"{consensus:.1f}/100")
    b.metric("Perubahan 1 jam", f"{selected['change1h']:.2f}%")
    c.metric("Likuiditas", money(selected["liquidity"]))
    d.metric("Rasio transaksi beli", f"{buy_ratio*100:.1f}%")
    st.write("**Penilaian per agen**")
    st.bar_chart(pd.Series(scores, name="Skor").sort_values(ascending=False))
    st.write("**Pemeriksaan risiko**")
    if risks:
        for risk in risks:
            st.warning(risk)
    else:
        st.info("Tidak ada flag pada pemeriksaan sederhana ini. Itu bukan berarti token bebas risiko.")
    st.caption(f"DEX: {selected['dex']} · Umur pool: {age:.1f} jam" if age is not None else f"DEX: {selected['dex']} · Umur pool tidak tersedia")
    if selected["url"]:
        st.link_button("Buka halaman pair di DexScreener", selected["url"])

st.divider()
st.subheader("🧪 Paper trading — simulasi saja")
st.caption("Order di bawah hanya mengubah saldo dan posisi virtual lokal pada sesi aplikasi. Harga eksekusi memakai harga snapshot yang sedang tampil; slippage, biaya, dan pajak tidak dimodelkan.")
if total_tokens:
    trade_token_label = st.selectbox("Token untuk simulasi", list(options.keys()), key="trade_token")
    trade_row = filtered[filtered["address"] == options[trade_token_label]].iloc[0]
    trade_amount = st.number_input("Nilai simulasi (USD)", min_value=1.0, max_value=10000.0,
                                   value=50.0, step=5.0)
    buy_col, sell_col = st.columns(2)
    with buy_col:
        if st.button("＋ Beli simulasi", use_container_width=True):
            if trade_row["price"] <= 0:
                st.error("Harga tidak valid.")
            elif trade_amount > st.session_state.cash:
                st.error("Saldo simulasi tidak cukup.")
            else:
                qty = trade_amount / trade_row["price"]
                pos = st.session_state.positions.get(trade_row["address"], {"symbol": trade_row["symbol"], "qty": 0.0, "cost": 0.0})
                pos["qty"] += qty
                pos["cost"] += trade_amount
                st.session_state.positions[trade_row["address"]] = pos
                st.session_state.cash -= trade_amount
                st.session_state.trades.append({"Waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Aksi": "BUY SIM", "Token": trade_row["symbol"], "Nilai USD": trade_amount})
                st.success("Pembelian simulasi dicatat.")
                st.rerun()
    with sell_col:
        if st.button("− Jual seluruh posisi simulasi token ini", use_container_width=True):
            pos = st.session_state.positions.get(trade_row["address"])
            if not pos or pos["qty"] <= 0:
                st.error("Belum ada posisi simulasi untuk token ini.")
            else:
                proceeds = pos["qty"] * max(trade_row["price"], 0)
                st.session_state.cash += proceeds
                st.session_state.trades.append({"Waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Aksi": "SELL SIM", "Token": trade_row["symbol"], "Nilai USD": proceeds})
                del st.session_state.positions[trade_row["address"]]
                st.success("Penjualan simulasi dicatat.")
                st.rerun()

positions_rows = []
market_value = 0.0
for address, pos in st.session_state.positions.items():
    current = df[df["address"] == address]
    price = float(current.iloc[0]["price"]) if not current.empty else 0.0
    value = pos["qty"] * price
    market_value += value
    positions_rows.append({"Token": pos["symbol"], "Jumlah virtual": pos["qty"],
                           "Modal USD": pos["cost"], "Nilai saat ini USD": value,
                           "P/L simulasi USD": value - pos["cost"]})
p1, p2, p3 = st.columns(3)
p1.metric("Kas simulasi", f"${st.session_state.cash:,.2f}")
p2.metric("Nilai posisi virtual", f"${market_value:,.2f}")
p3.metric("Total ekuitas simulasi", f"${st.session_state.cash + market_value:,.2f}")
if positions_rows:
    st.dataframe(pd.DataFrame(positions_rows), use_container_width=True, hide_index=True)
else:
    st.info("Belum ada posisi virtual.")
if st.session_state.trades:
    st.write("**Riwayat simulasi**")
    st.dataframe(pd.DataFrame(st.session_state.trades).iloc[::-1], use_container_width=True, hide_index=True)

st.divider()
st.caption("Catatan metodologi: DexScreener menyediakan snapshot harga, likuiditas, volume, perubahan harga, dan transaksi pair. Aplikasi ini tidak memiliki data historis candle bawaan dari endpoint yang digunakan; skor agen adalah aturan transparan dari snapshot, bukan model AI terlatih. Data dapat terlambat, tidak lengkap, atau berubah.")
st.caption("Dibuat untuk pembelajaran analisis data dan pengujian strategi secara virtual.")
