import client from './client.js'

/** Fetch all pipeline runs. */
export async function fetchRuns() {
  const { data } = await client.get('/api/v1/pipeline/runs')
  return data
}

/**
 * Trigger a new pipeline run.
 * @param {{ pipeline_id: string, name?: string, sources?: string[] }} payload
 */
export async function triggerRun(payload) {
  const { data } = await client.post('/api/v1/pipeline/run', payload)
  return data
}

/**
 * Fetch status for a specific run.
 * @param {string} runId
 */
export async function fetchRunStatus(runId) {
  const { data } = await client.get(`/api/v1/pipeline/status/${runId}`)
  return data
}

/**
 * Cancel a running pipeline.
 * @param {string} runId
 */
export async function cancelRun(runId) {
  const { data } = await client.post(`/api/v1/pipeline/cancel/${runId}`)
  return data
}
