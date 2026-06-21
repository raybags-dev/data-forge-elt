import client from './client.js'

/** Fetch all dataset metadata records. */
export async function fetchDatasets() {
  const { data } = await client.get('/api/v1/datasets')
  return data
}

/** Fetch warehouse table list. */
export async function fetchTables() {
  const { data } = await client.get('/api/v1/datasets/tables')
  return data
}

/**
 * Fetch a preview of rows from a named table.
 * @param {string} tableName
 * @param {number} [limit=100]
 */
export async function fetchPreview(tableName, limit = 100) {
  const { data } = await client.get(`/api/v1/datasets/preview/${tableName}`, {
    params: { limit },
  })
  return data
}
