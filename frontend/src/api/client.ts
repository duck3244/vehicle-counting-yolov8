import axios from 'axios'
import type { Health, Job } from '../types'

// Vite 프록시가 /api 와 /static 을 백엔드로 포워딩한다.
const http = axios.create({
  baseURL: '',
  timeout: 30_000,
})

export async function fetchHealth(): Promise<Health> {
  const { data } = await http.get<Health>('/api/health')
  return data
}

export async function listJobs(): Promise<Job[]> {
  const { data } = await http.get<Job[]>('/api/jobs')
  return data
}

export async function getJob(id: string): Promise<Job> {
  const { data } = await http.get<Job>(`/api/jobs/${id}`)
  return data
}

export interface CreateJobParams {
  file: File
  lanes?: number | null
  confidence_threshold?: number | null
  model_path?: string | null
  onUploadProgress?: (progress: number) => void
}

export async function createJob(params: CreateJobParams): Promise<Job> {
  const form = new FormData()
  form.append('file', params.file)
  if (params.lanes != null) form.append('lanes', String(params.lanes))
  if (params.confidence_threshold != null)
    form.append('confidence_threshold', String(params.confidence_threshold))
  if (params.model_path) form.append('model_path', params.model_path)

  const { data } = await http.post<Job>('/api/jobs', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 0, // 업로드는 오래 걸릴 수 있음
    onUploadProgress: (evt) => {
      if (params.onUploadProgress && evt.total) {
        params.onUploadProgress(evt.loaded / evt.total)
      }
    },
  })
  return data
}
