import { defineStore } from 'pinia'
import { ref } from 'vue'
import { createJob, getJob, listJobs, type CreateJobParams } from '../api/client'
import type { Job } from '../types'

export const useJobsStore = defineStore('jobs', () => {
  const jobs = ref<Job[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function refresh(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      jobs.value = await listJobs()
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      loading.value = false
    }
  }

  async function create(params: CreateJobParams): Promise<Job> {
    const job = await createJob(params)
    // 최신 잡을 목록 앞쪽에 병합
    jobs.value = [job, ...jobs.value.filter((j) => j.id !== job.id)]
    return job
  }

  async function fetchOne(id: string): Promise<Job> {
    const job = await getJob(id)
    const idx = jobs.value.findIndex((j) => j.id === id)
    if (idx >= 0) jobs.value[idx] = job
    return job
  }

  return { jobs, loading, error, refresh, create, fetchOne }
})
