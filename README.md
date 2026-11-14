# 楽譜移調アプリ (transposition)

PDF またはスマホ写真(JPEG/PNG)の楽譜をアップロードすると、OMR(光学楽譜認識)で
読み取り、指定した半音数 / 調に移調した楽譜を PDF としてダウンロードできる Web アプリ。

## 構成

- `backend/` — FastAPI。OMR(Audiveris, Dockerで実行) → 移調(music21) → PDF描画(verovio + cairosvg) のパイプライン。
- `frontend/` — React + TypeScript (Vite)。アップロード、移調指定、ダウンロードの UI。

## 動作に必要なもの

- Docker (OMR エンジン Audiveris を実行するため。ホストの glibc が古くても動くよう、
  Ubuntu22.04 コンテナ内で動かしている)
- Python 3.8+
- Node.js 18+

## セットアップ

```bash
# 1. Audiveris の Docker イメージをビルド(初回のみ)
backend/scripts/build_audiveris_image.sh

# 2. バックエンド
cd backend
python3 -m venv venv   # venv が使えない環境では: pip install --user virtualenv && python3 -m virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 3. フロントエンド(別ターミナル)
cd frontend
npm install
npm run dev
```

ブラウザで `http://localhost:5173` を開く。Vite の dev サーバーが `/api/*` を
`http://127.0.0.1:8000` にプロキシする(`frontend/vite.config.ts`)。

## 処理の流れ

1. `POST /api/jobs` にファイルをアップロード → ジョブを作成し、バックグラウンドで
   Audiveris (Docker) を実行して MusicXML を抽出。
2. フロントエンドが `GET /api/jobs/{id}` をポーリングし、`ready` になったら
   検出された調・パート数・小節数を表示。
3. `POST /api/jobs/{id}/transpose` で半音数 or 目的の調を指定 → music21 で移調し、
   verovio で楽譜に描画した SVG を PDF に変換。
4. `GET /api/jobs/{id}/download` で完成した PDF を取得。

## 既知の制約

- OMR の精度は元画像の解像度・傾き・印刷品質に強く依存する。画像が小さすぎる場合は
  自動的にアップスケールするが、極端に不鮮明な写真では認識に失敗することがある。
- OMR が誤認識したリズム(小節の長さが合わない等)を含む結果は、PDF 書き出し時に
  複数のフォールバック(`backend/app/jobs.py` の `_export_musicxml`)を試みるが、
  それでも失敗する場合はエラーメッセージが表示される。
- ジョブ状態はメモリ上のみで保持しており、バックエンド再起動で失われる(永続化なし)。
