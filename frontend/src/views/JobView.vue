<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { getJob } from '../api/client'
import type { Job } from '../types'

const route = useRoute()
const jobId = computed(() => String(route.params.id))

const job = ref<Job | null>(null)
const error = ref<string | null>(null)
let pollTimer: number | undefined

async function load() {
  try {
    job.value = await getJob(jobId.value)
    error.value = null
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

function scheduleNext() {
  if (!job.value) return
  if (job.value.status === 'done' || job.value.status === 'error') return
  // 실행 중이면 1초, queued 면 2초 간격
  const interval = job.value.status === 'running' ? 1000 : 2000
  pollTimer = window.setTimeout(async () => {
    await load()
    scheduleNext()
  }, interval)
}

onMounted(async () => {
  await load()
  scheduleNext()
})

onBeforeUnmount(() => {
  if (pollTimer) window.clearTimeout(pollTimer)
})

const progressPct = computed(() =>
  job.value ? (job.value.progress * 100).toFixed(1) + '%' : '-'
)
const badgeClass = computed(() =>
  job.value ? `badge badge-${job.value.status}` : 'badge'
)
const videoUrl = computed(() => job.value?.result?.artifacts?.video ?? null)
const chartUrl = computed(() => job.value?.result?.artifacts?.results_chart ?? null)
const hourlyUrl = computed(
  () => job.value?.result?.artifacts?.results_hourly ?? null
)
const totalCounts = computed(() => job.value?.result?.total_counts ?? null)
const grandTotal = computed(() => {
  if (!totalCounts.value) return 0
  return Object.values(totalCounts.value).reduce((a, b) => a + b, 0)
})

function fmt(ts: string | null): string {
  return ts ? new Date(ts).toLocaleString() : '-'
}
</script>

<template>
  <p><RouterLink to="/">← 목록으로</RouterLink></p>

  <section v-if="error" class="panel">
    <p class="err">{{ error }}</p>
  </section>

  <section v-else-if="!job" class="panel">
    <p class="muted">로딩 중…</p>
  </section>

  <template v-else>
    <section class="panel">
      <h2>잡 <code>{{ job.id }}</code></h2>
      <table>
        <tbody>
          <tr>
            <th>상태</th>
            <td><span :class="badgeClass">{{ job.status }}</span></td>
          </tr>
          <tr>
            <th>파일명</th>
            <td>{{ job.filename }}</td>
          </tr>
          <tr>
            <th>옵션</th>
            <td class="muted">
              lanes={{ job.options.lanes ?? '기본' }},
              conf={{ job.options.confidence_threshold ?? '기본' }}
            </td>
          </tr>
          <tr>
            <th>생성</th>
            <td class="muted">{{ fmt(job.created_at) }}</td>
          </tr>
          <tr>
            <th>시작</th>
            <td class="muted">{{ fmt(job.started_at) }}</td>
          </tr>
          <tr>
            <th>종료</th>
            <td class="muted">{{ fmt(job.finished_at) }}</td>
          </tr>
        </tbody>
      </table>

      <div v-if="job.status === 'running' || job.status === 'queued'" style="margin-top: 1rem;">
        <label>진행률 ({{ progressPct }})</label>
        <progress :value="job.progress" max="1" />
        <p class="muted">
          {{ job.current_frame }} / {{ job.total_frames || '?' }} 프레임
        </p>
      </div>

      <p v-if="job.status === 'error' && job.error" class="err">
        오류: {{ job.error }}
      </p>
    </section>

    <section v-if="job.status === 'done'" class="panel">
      <h2>결과 영상</h2>
      <video
        v-if="videoUrl"
        :src="videoUrl"
        controls
        style="width: 100%; max-height: 480px; background: #000;"
      />
      <p v-else class="muted">영상 파일이 없습니다.</p>
    </section>

    <section v-if="job.status === 'done' && totalCounts" class="panel">
      <h2>카운트 요약</h2>
      <p>
        <strong>총 {{ grandTotal }}대</strong>
      </p>
      <table>
        <thead>
          <tr><th>차량 타입</th><th>수</th></tr>
        </thead>
        <tbody>
          <tr v-for="(v, k) in totalCounts" :key="k">
            <td>{{ k }}</td>
            <td>{{ v }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section v-if="job.status === 'done' && (chartUrl || hourlyUrl)" class="panel">
      <h2>차트</h2>
      <div v-if="chartUrl">
        <img :src="chartUrl" style="max-width: 100%;" alt="counting chart" />
      </div>
      <div v-if="hourlyUrl" style="margin-top: 1rem;">
        <img :src="hourlyUrl" style="max-width: 100%;" alt="hourly chart" />
      </div>
    </section>
  </template>
</template>
