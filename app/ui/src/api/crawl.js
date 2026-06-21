import client from './client.js'

/** Fetch crawler status for all sources. */
export async function fetchCrawlerStatus() {
  const { data } = await client.get('/api/v1/crawl/status')
  return data
}

/**
 * Trigger a crawl for a specific source.
 * @param {{ source: string, urls?: string[] }} payload
 */
export async function triggerCrawl(payload) {
  const { data } = await client.post('/api/v1/crawl/run', payload)
  return data
}

/**
 * Download a Kaggle dataset.
 * @param {{ dataset: string, path?: string }} payload
 */
export async function downloadKaggle(payload) {
  const { data } = await client.post('/api/v1/kaggle/download', payload)
  return data
}
