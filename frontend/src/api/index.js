import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// Request interceptor - add X-Auth-Token header
api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers['X-Auth-Token'] = token
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// Response interceptor - error handling
api.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    const { response } = error
    let errorMessage = 'An unexpected error occurred'

    if (response) {
      switch (response.status) {
        case 400:
          errorMessage = response.data?.message || 'Bad request'
          break
        case 401:
          errorMessage = 'Unauthorized - please check your authentication'
          break
        case 403:
          errorMessage = 'Forbidden - access denied'
          break
        case 404:
          errorMessage = response.data?.message || 'Resource not found'
          break
        case 500:
          errorMessage = response.data?.message || 'Internal server error'
          break
        default:
          errorMessage = response.data?.message || `Server error: ${response.status}`
      }
    } else if (error.code === 'ECONNABORTED') {
      errorMessage = 'Request timeout'
    } else if (error.message === 'Network Error') {
      errorMessage = 'Network error - please check your connection'
    }

    console.error('API Error:', errorMessage)
    return Promise.reject(new Error(errorMessage))
  }
)

/**
 * Analyze a release
 * @param {string} releaseNo - Release number to analyze
 * @returns {Promise} Task creation result
 */
export function analyze(releaseNo) {
  return api.post('/analyze', { release_no: releaseNo })
}

/**
 * Get task status
 * @param {string} taskId - Task ID
 * @returns {Promise} Task details
 */
export function getTask(taskId) {
  return api.get(`/task/${taskId}`)
}

/**
 * Get analysis report
 * @param {string} taskId - Task ID
 * @returns {Promise} Report data
 */
export function getReport(taskId) {
  return api.get(`/report/${taskId}`)
}

/**
 * Mark report as reviewed
 * @param {string} taskId - Task ID
 * @param {Object} data - Mark data (e.g., status, notes)
 * @returns {Promise} Mark result
 */
export function mark(taskId, data) {
  return api.post(`/report/${taskId}/mark`, data)
}

/**
 * Get analysis history
 * @param {number} limit - Number of records to return (optional)
 * @returns {Promise} History list
 */
export function getHistory(limit = 20) {
  return api.get('/history', { params: { limit } })
}

/**
 * Webhook endpoint for operations
 * @param {Object} data - Webhook payload
 * @returns {Promise} Webhook result
 */
export function webhook(data) {
  return api.post('/webhook/op', data)
}

export default api
