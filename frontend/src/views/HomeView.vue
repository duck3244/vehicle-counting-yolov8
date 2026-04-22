<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchHealth } from '../api/client'
import { useJobsStore } from '../stores/jobs'
import type { Health, Job } from '../types'

const router = useRouter()
const store = useJobsStore()

const health = ref<Health | null>(null)
const healthError = ref<string | null>(null)

const file = ref<File | null>(null)
const lanes = ref<number | null>(3)
const conf = ref<number | null>(0.5)
const submitting = ref(false)
const uploadProgress = ref(0)
const submitError = ref<string | null>(null)

function onFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  file.value = target.files && target.files.length ? target.files[0] : null
}

const canSubmit = computed(() => file.value !== null && !submitting.value)

async function submit() {
  if (!file.value) return
  submitting.value = true
  submitError.value = null
  uploadProgress.value = 0
  try {
    const job = await store.create({
      file: file.value,
      lanes: lanes.value,
      confidence_threshold: conf.value,
      onUploadProgress: (p) => (uploadProgress.value = p),
    })
    router.push({ name: 'job', params: { id: job.id } })
  } catch (e: unknown) {
    submitError.value = e instanceof Error ? e.message : String(e)
  } finally {
    submitting.value = false
  }
}

function badgeClass(j: Job) {
  return `badge badge-${j.status}`
}
function pct(j: Job) {
  return (j.progress * 100).toFixed(0) + '%'
}

let refreshTimer: number | undefined

onMounted(async () => {
  try {
    health.value = await fetchHealth()
  } catch (e) {
    healthError.value = e instanceof Error ? e.message : String(e)
  }
  await store.refresh()
  // 실행 중인 잡이 있을 때만 목록 폴링
  refreshTimer = window.setInterval(() => {
    if (store.jobs.some((j) => j.status === 'running' || j.status === 'queued')) {
      store.refresh()
    }
  }, 3000)
})

// 컴포넌트 파괴 시 타이머 정리
import { onBeforeUnmount } from 'vue'
onBeforeUnmount(() => {
  if (refreshTimer) window.clearInterval(refreshTimer)
})
</script>

<template>
  <section class="panel">
    <h2>백엔드 상태</h2>
    <p v-if="healthError" class="err">에러: {{ healthError }}</p>
    <p v-else-if="!health" class="muted">확인 중…</p>
    <p v-else>
      <span class="badge badge-done">{{ health.status }}</span>
      &nbsp;GPU: <strong>{{ health.gpu ?? '없음' }}</strong>
      &nbsp;<span class="muted">API {{ health.version }}</span>
    </p>
  </section>

  <section class="panel">
    <h2>새 잡 만들기</h2>
    <form @submit.prevent="submit">
      <label>비디오 파일 (.mp4/.avi/.mov/.mkv/.webm)</label>
      <input type="file" accept="video/*" @change="onFileChange" />

      <div class="row" style="margin-top: 1rem;">
        <div>
          <label>차선 수 (1–20, 선택)</label>
          <input type="number" v-model.number="lanes" min="1" max="20" />
        </div>
        <div>
          <label>신뢰도 임계값 (0.0–1.0, 선택)</label>
          <input type="number" v-model.number="conf" min="0" max="1" step="0.05" />
        </div>
      </div>

      <div v-if="submitting" style="margin-top: 1rem;">
        <label>업로드 진행</label>
        <progress :value="uploadProgress" max="1" />
        <p class="muted">{{ (uploadProgress * 100).toFixed(0) }}%</p>
      </div>

      <p v-if="submitError" class="err">{{ submitError }}</p>

      <button type="submit" :disabled="!canSubmit" style="margin-top: 1rem;">
        {{ submitting ? '업로드 중…' : '잡 시작' }}
      </button>
    </form>
  </section>

  <section class="panel">
    <div style="display: flex; justify-content: space-between; align-items: center;">
      <h2 style="margin: 0;">잡 목록</h2>
      <button @click="store.refresh()" :disabled="store.loading">새로고침</button>
    </div>
    <p v-if="store.error" class="err">{{ store.error }}</p>
    <p v-else-if="store.jobs.length === 0" class="muted">잡이 없습니다.</p>
    <table v-else style="margin-top: 1rem;">
      <thead>
        <tr>
          <th>ID</th>
          <th>파일명</th>
          <th>상태</th>
          <th>진행률</th>
          <th>생성 시각</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="j in store.jobs" :key="j.id">
          <td><code>{{ j.id }}</code></td>
          <td>{{ j.filename }}</td>
          <td><span :class="badgeClass(j)">{{ j.status }}</span></td>
          <td>{{ pct(j) }}</td>
          <td class="muted">{{ new Date(j.created_at).toLocaleString() }}</td>
          <td>
            <RouterLink :to="{ name: 'job', params: { id: j.id } }">상세</RouterLink>
          </td>
        </tr>
      </tbody>
    </table>
  </section>
</template>
