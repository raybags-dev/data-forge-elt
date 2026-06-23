import axios from 'axios'

/**
 * Axios instance pre-configured with the DataForge API base URL.
 * The base URL is read from VITE_API_BASE_URL env var or defaults to
 * an empty string (Vite dev proxy forwards /api/* to http://localhost:8000).
 */
const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8002',
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json',
  },
})

client.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.detail ??
      error.response?.data?.message ??
      error.message ??
      'Unknown error'
    return Promise.reject(new Error(message))
  },
)

export default client
