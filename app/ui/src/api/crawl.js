import client from './client.js'

export async function fetchCrawlerStatus() {
  const { data } = await client.get('/api/v1/crawl/status')
  return data
}

export async function triggerCrawl(payload) {
  const { data } = await client.post('/api/v1/crawl', payload)
  return data
}

export async function analyzeCrawl(payload) {
  const { data } = await client.post('/api/v1/crawl/analyze', payload)
  return data
}

export async function getSources() {
  const { data } = await client.get('/api/v1/crawl/sources')
  return data
}

export async function downloadKaggle(payload) {
  const { data } = await client.post('/api/v1/kaggle/download', payload)
  return data
}
