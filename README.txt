# AI Trading Crew — Solana (Paper Trading)

## Jalankan di Windows

1. Install Python 3.10 atau lebih baru.
2. Simpan `ai_trading_crew.py` dan `requirements.txt` dalam satu folder.
3. Buka CMD pada folder tersebut, lalu jalankan:

```bash
python -m pip install -r requirements.txt
python -m streamlit run ai_trading_crew.py
```

Dashboard akan terbuka di `http://localhost:8501`.

## Fitur
- Data pair Solana publik dari DexScreener.
- Lima agen skor heuristik: Sniper, Momentum, Dip Hunter, Whale Tail proxy, Scalper.
- Filter likuiditas dan ambang skor.
- Peta risiko/momentum.
- Paper wallet virtual $1,000 dan riwayat simulasi.

## Batasan penting
- Tidak ada wallet, private key, atau eksekusi transaksi sungguhan.
- Skor bukan prediksi dan bukan saran investasi.
- Whale Tail hanya proxy aktivitas pair dari rasio transaksi/volume, bukan identifikasi wallet paus.
- Data snapshot DexScreener tidak menyediakan histori candle pada endpoint yang digunakan.
- Saldo dan posisi disimpan di session state; reset atau sesi baru dapat menghapus simulasi.
