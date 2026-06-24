import client from './client.js'

export async function fetchCrawlerStatus() {
  const { data } = await client.get('/api/v1/crawl/status')
  return data
}

function tokenHeader(appToken) {
  const tok = appToken || sessionStorage.getItem('df_app_token')
  return tok ? { 'X-App-Token': tok } : {}
}

export async function triggerCrawl(payload) {
  const { appToken, ...body } = payload
  const { data } = await client.post('/api/v1/crawl', body, { headers: tokenHeader(appToken) })
  return data
}

export async function analyzeCrawl(payload) {
  const { appToken, ...body } = payload
  const { data } = await client.post('/api/v1/crawl/analyze', body, { headers: tokenHeader(appToken) })
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

export async function parseCurl(payload) {
  const { data } = await client.post('/api/v1/crawl/parse-curl', payload)
  return data
}
