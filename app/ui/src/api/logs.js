import client from './client.js'

/**
 * Fetch recent log lines from the API.
 * @param {{ level?: string, lines?: number }} [params]
 */
export async function getLogs(params = {}) {
  const { data } = await client.get('/api/v1/logs', { params })
  return data
}
