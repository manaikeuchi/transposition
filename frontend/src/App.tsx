import { useCallback, useEffect, useRef, useState } from "react";
import "./App.css";
import {
  type JobStatus,
  downloadUrl,
  getJob,
  requestTranspose,
  uploadScore,
} from "./api";

const KEY_OPTIONS = [
  "C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B",
];

const POLL_INTERVAL_MS = 1500;

function statusLabel(status: JobStatus["status"]): string {
  switch (status) {
    case "omr_processing":
      return "楽譜を認識しています…";
    case "ready":
      return "認識完了。移調方法を選んでください。";
    case "rendering":
      return "移調した楽譜を生成しています…";
    case "done":
      return "完成しました。";
    case "omr_failed":
      return "楽譜の認識に失敗しました。";
    case "render_failed":
      return "移調後の楽譜生成に失敗しました。";
  }
}

export default function App() {
  const [job, setJob] = useState<JobStatus | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [mode, setMode] = useState<"semitones" | "key">("semitones");
  const [semitones, setSemitones] = useState(0);
  const [targetKey, setTargetKey] = useState("C");
  const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollTimer.current) {
      clearTimeout(pollTimer.current);
      pollTimer.current = null;
    }
  }, []);

  useEffect(() => {
    if (!job) return;
    if (job.status !== "omr_processing" && job.status !== "rendering") return;

    let cancelled = false;
    const jobId = job.job_id;

    const tick = async () => {
      try {
        const updated = await getJob(jobId);
        if (!cancelled) setJob(updated);
      } catch {
        // transient network error; just retry on the next tick
      }
      if (!cancelled) {
        pollTimer.current = setTimeout(tick, POLL_INTERVAL_MS);
      }
    };
    pollTimer.current = setTimeout(tick, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      stopPolling();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [job?.job_id, job?.status, stopPolling]);

  async function handleFileSelected(file: File) {
    setUploadError(null);
    setUploading(true);
    stopPolling();
    try {
      const created = await uploadScore(file);
      setJob(created);
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : String(e));
    } finally {
      setUploading(false);
    }
  }

  async function handleTranspose() {
    if (!job) return;
    try {
      const updated = await requestTranspose(
        job.job_id,
        mode === "semitones"
          ? { mode: "semitones", semitones }
          : { mode: "key", target_key: targetKey },
      );
      setJob(updated);
    } catch (e) {
      setJob({
        ...job,
        status: "render_failed",
        error: e instanceof Error ? e.message : String(e),
      });
    }
  }

  function reset() {
    stopPolling();
    setJob(null);
    setUploadError(null);
  }

  return (
    <div className="page">
      <h1>楽譜移調アプリ</h1>
      <p className="subtitle">
        PDF または 写真(JPEG/PNG) の楽譜をアップロードすると、自動認識して移調したPDFを作成します。
      </p>

      {!job && (
        <UploadArea uploading={uploading} onFile={handleFileSelected} />
      )}
      {uploadError && <p className="error">{uploadError}</p>}

      {job && (
        <div className="job-panel">
          <p className="status-line">{statusLabel(job.status)}</p>

          {(job.status === "omr_processing" || job.status === "rendering") && (
            <div className="spinner" aria-label="処理中" />
          )}

          {job.status === "ready" && (
            <>
              <dl className="info">
                <dt>検出された調</dt>
                <dd>{job.detected_key ?? "判定できませんでした"}</dd>
                <dt>パート数</dt>
                <dd>{job.part_count ?? "-"}</dd>
                <dt>小節数</dt>
                <dd>{job.measure_count ?? "-"}</dd>
              </dl>

              <TransposeForm
                mode={mode}
                setMode={setMode}
                semitones={semitones}
                setSemitones={setSemitones}
                targetKey={targetKey}
                setTargetKey={setTargetKey}
                onSubmit={handleTranspose}
              />
            </>
          )}

          {job.status === "done" && (
            <div className="result">
              <a className="download-btn" href={downloadUrl(job.job_id)} download>
                移調後のPDFをダウンロード
              </a>
              <button className="link-btn" onClick={() => setJob({ ...job, status: "ready" })}>
                別の移調を試す
              </button>
            </div>
          )}

          {(job.status === "omr_failed" || job.status === "render_failed") && (
            <>
              <p className="error">{job.error}</p>
              {job.status === "render_failed" && (
                <TransposeForm
                  mode={mode}
                  setMode={setMode}
                  semitones={semitones}
                  setSemitones={setSemitones}
                  targetKey={targetKey}
                  setTargetKey={setTargetKey}
                  onSubmit={handleTranspose}
                />
              )}
            </>
          )}

          <button className="link-btn" onClick={reset}>
            別の楽譜をアップロードする
          </button>
        </div>
      )}
    </div>
  );
}

function UploadArea({
  uploading,
  onFile,
}: {
  uploading: boolean;
  onFile: (file: File) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  return (
    <div
      className={`dropzone ${dragOver ? "dragover" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        const file = e.dataTransfer.files?.[0];
        if (file) onFile(file);
      }}
      onClick={() => inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.jpg,.jpeg,.png,.tif,.tiff"
        hidden
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onFile(file);
        }}
      />
      {uploading ? (
        <p>アップロード中…</p>
      ) : (
        <p>
          クリックしてファイルを選択、または
          <br />
          ここにドラッグ＆ドロップ
          <br />
          <span className="hint">PDF / JPEG / PNG</span>
        </p>
      )}
    </div>
  );
}

function TransposeForm({
  mode,
  setMode,
  semitones,
  setSemitones,
  targetKey,
  setTargetKey,
  onSubmit,
}: {
  mode: "semitones" | "key";
  setMode: (m: "semitones" | "key") => void;
  semitones: number;
  setSemitones: (n: number) => void;
  targetKey: string;
  setTargetKey: (k: string) => void;
  onSubmit: () => void;
}) {
  return (
    <div className="transpose-form">
      <div className="mode-toggle">
        <label>
          <input
            type="radio"
            checked={mode === "semitones"}
            onChange={() => setMode("semitones")}
          />
          半音数で指定
        </label>
        <label>
          <input
            type="radio"
            checked={mode === "key"}
            onChange={() => setMode("key")}
          />
          調で指定
        </label>
      </div>

      {mode === "semitones" ? (
        <div className="semitone-control">
          <button type="button" onClick={() => setSemitones(semitones - 1)}>
            −
          </button>
          <span className="semitone-value">
            {semitones > 0 ? `+${semitones}` : semitones}
          </span>
          <button type="button" onClick={() => setSemitones(semitones + 1)}>
            ＋
          </button>
        </div>
      ) : (
        <select value={targetKey} onChange={(e) => setTargetKey(e.target.value)}>
          {KEY_OPTIONS.map((k) => (
            <option key={k} value={k}>
              {k}
            </option>
          ))}
        </select>
      )}

      <button className="primary-btn" onClick={onSubmit}>
        移調してPDFを作成
      </button>
    </div>
  );
}
