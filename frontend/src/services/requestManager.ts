/**
 * Request Manager with Retry Logic and Cancellation Support
 * Handles retries, request deduplication, and proper cancellation
 */

interface RequestOptions extends RequestInit {
  maxRetries?: number
  retryDelay?: number
  timeout?: number
  dedupe?: boolean
}

interface RetryConfig {
  maxRetries: number
  retryDelay: number
  backoffMultiplier: number
}

class RequestManager {
  private activeRequests: Map<string, Promise<Response>> = new Map()
  private abortControllers: Map<string, AbortController> = new Map()
  
  private readonly defaultRetryConfig: RetryConfig = {
    maxRetries: 3,
    retryDelay: 1000, // Start with 1 second
    backoffMultiplier: 2 // Double the delay each retry
  }

  /**
   * Make a fetch request with retry logic and cancellation support
   */
  async fetchWithRetry(
    url: string, 
    options: RequestOptions = {}
  ): Promise<Response> {
    const {
      maxRetries = this.defaultRetryConfig.maxRetries,
      retryDelay = this.defaultRetryConfig.retryDelay,
      timeout = 30000, // 30 seconds default
      dedupe = false,
      ...fetchOptions
    } = options

    // Generate request key for deduplication
    const requestKey = dedupe ? this.generateRequestKey(url, fetchOptions) : null

    // Check for existing request if deduplication is enabled
    if (requestKey && this.activeRequests.has(requestKey)) {
      console.log(`Request deduplication: Reusing existing request for ${url}`)
      return this.activeRequests.get(requestKey)!
    }

    // Create abort controller for this request
    const abortController = new AbortController()
    const requestId = `${url}-${Date.now()}`
    this.abortControllers.set(requestId, abortController)

    // Set up timeout
    const timeoutId = setTimeout(() => {
      abortController.abort()
    }, timeout)

    // Create the request promise
    const requestPromise = this.executeWithRetry(
      url,
      {
        ...fetchOptions,
        signal: abortController.signal
      },
      maxRetries,
      retryDelay,
      requestId
    ).finally(() => {
      clearTimeout(timeoutId)
      this.abortControllers.delete(requestId)
      if (requestKey) {
        this.activeRequests.delete(requestKey)
      }
    })

    // Store for deduplication if enabled
    if (requestKey) {
      this.activeRequests.set(requestKey, requestPromise)
    }

    return requestPromise
  }

  /**
   * Execute request with retry logic
   */
  private async executeWithRetry(
    url: string,
    options: RequestInit,
    retriesLeft: number,
    currentDelay: number,
    requestId: string
  ): Promise<Response> {
    try {
      const response = await fetch(url, options)

      // Check if response is ok or if it's a client error that shouldn't be retried
      if (response.ok || response.status >= 400 && response.status < 500) {
        return response
      }

      // Server error - might be worth retrying
      throw new Error(`Server error: ${response.status}`)
    } catch (error: any) {
      // Check if request was aborted
      if (error.name === 'AbortError') {
        console.log(`Request aborted: ${url}`)
        throw error
      }

      // Check if we have retries left
      if (retriesLeft <= 0) {
        console.error(`All retries exhausted for ${url}:`, error)
        throw error
      }

      // Log retry attempt
      console.log(`Retrying request to ${url}. Retries left: ${retriesLeft}. Delay: ${currentDelay}ms`)

      // Wait before retry
      await this.delay(currentDelay)

      // Check if request was cancelled during delay
      const controller = this.abortControllers.get(requestId)
      if (controller?.signal.aborted) {
        throw new Error('Request cancelled during retry delay')
      }

      // Retry with exponential backoff
      return this.executeWithRetry(
        url,
        options,
        retriesLeft - 1,
        currentDelay * this.defaultRetryConfig.backoffMultiplier,
        requestId
      )
    }
  }

  /**
   * Cancel a specific request
   */
  cancelRequest(requestId: string): void {
    const controller = this.abortControllers.get(requestId)
    if (controller) {
      controller.abort()
      this.abortControllers.delete(requestId)
    }
  }

  /**
   * Cancel all active requests
   */
  cancelAllRequests(): void {
    this.abortControllers.forEach(controller => controller.abort())
    this.abortControllers.clear()
    this.activeRequests.clear()
  }

  /**
   * Generate a unique key for request deduplication
   */
  private generateRequestKey(url: string, options: RequestInit): string {
    const method = options.method || 'GET'
    const body = options.body ? JSON.stringify(options.body) : ''
    return `${method}:${url}:${body}`
  }

  /**
   * Delay helper for retries
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms))
  }

  /**
   * Make authenticated request with retry
   */
  async authenticatedFetch(
    url: string,
    token: string,
    options: RequestOptions = {}
  ): Promise<Response> {
    return this.fetchWithRetry(url, {
      ...options,
      headers: {
        ...options.headers,
        'Authorization': `Bearer ${token}`
      }
    })
  }
}

// Export singleton instance
export const requestManager = new RequestManager()

// Export types
export type { RequestOptions, RetryConfig }