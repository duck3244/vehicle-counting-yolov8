// 백엔드 Pydantic 스키마와 동기화해야 하는 공용 타입

export type JobStatus = 'queued' | 'running' | 'done' | 'error'

export interface JobOptions {
  lanes: number | null
  confidence_threshold: number | null
  model_path: string | null
}

export interface JobResultArtifacts {
  video?: string
  results_json?: string
  results_chart?: string
  results_hourly?: string
  [key: string]: string | undefined
}

export interface JobResult {
  artifacts: JobResultArtifacts
  total_counts: Record<string, number> | null
  summary: Record<string, unknown> | null
  session: Record<string, unknown> | null
}

export interface Job {
  id: string
  status: JobStatus
  filename: string
  created_at: string
  started_at: string | null
  finished_at: string | null
  progress: number // 0.0 ~ 1.0
  current_frame: number
  total_frames: number
  message: string | null
  options: JobOptions
  result: JobResult | null
  error: string | null
}

export interface Health {
  status: string
  gpu: string | null
  version: string
}
