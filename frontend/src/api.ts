export type JobStatus = {
  job_id: string;
  status:
    | "omr_processing"
    | "omr_failed"
    | "ready"
    | "rendering"
    | "done"
    | "render_failed";
  detected_key: string | null;
  part_count: number | null;
  measure_count: number | null;
  error: string | null;
};

export type TransposeRequest =
  | { mode: "semitones"; semitones: number }
  | { mode: "key"; target_key: string };

async function asJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail || `リクエストに失敗しました (HTTP ${res.status})`);
  }
  return res.json();
}

export async function uploadScore(file: File): Promise<JobStatus> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/jobs", { method: "POST", body: form });
  return asJson(res);
}

export async function getJob(jobId: string): Promise<JobStatus> {
  const res = await fetch(`/api/jobs/${jobId}`);
  return asJson(res);
}

export async function requestTranspose(
  jobId: string,
  req: TransposeRequest,
): Promise<JobStatus> {
  const res = await fetch(`/api/jobs/${jobId}/transpose`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  return asJson(res);
}

export function downloadUrl(jobId: string): string {
  return `/api/jobs/${jobId}/download`;
}
