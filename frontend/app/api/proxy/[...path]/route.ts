import { NextRequest, NextResponse } from 'next/server'

// Use environment variable or default to local backend (host.docker.internal for Docker)
const BACKEND_URL = process.env.BACKEND_URL || 'http://host.docker.internal:8000'
const PROXY_TIMEOUT = 180000 // 3 minutes (matches API client expectations for heavy endpoints)

console.log('Proxy Backend URL:', BACKEND_URL)
console.log('Docker Environment:', process.env.DOCKER_ENV)

/**
 * Enhanced proxy to handle cookie-based authentication
 * Forwards cookies in both directions for HttpOnly cookie support
 * Includes error handling and timeout management
 */

function mergeHeaders(...sources: Array<HeadersInit | undefined | null>) {
  const result: Record<string, string> = {}
  for (const source of sources) {
    if (!source) continue
    if (source instanceof Headers) {
      source.forEach((value, key) => {
        result[key] = value
      })
    } else if (Array.isArray(source)) {
      // Handle [string, string][] format
      source.forEach(([key, value]) => {
        result[key] = value
      })
    } else {
      // Handle Record<string, string> format
      Object.assign(result, source)
    }
  }
  return result
}

async function handleProxyRequest(
  url: string,
  options: RequestInit,
  redirectCount = 0
): Promise<Response> {
  try {
    // Create AbortController for timeout and combine with caller signal if provided
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), PROXY_TIMEOUT)

    const { signal: callerSignal, ...restOptions } = options
    const signals = [controller.signal]
    if (callerSignal) {
      signals.push(callerSignal)
    }
    const combinedSignal = signals.length > 1 ? AbortSignal.any(signals) : signals[0]

    const response = await fetch(url, {
      ...restOptions,
      headers: mergeHeaders(restOptions.headers),
      redirect: 'manual',
      signal: combinedSignal,
    })

    clearTimeout(timeoutId)

    // Manually follow redirects so we never drop auth headers
    if ([301, 302, 303, 307, 308].includes(response.status)) {
      const location = response.headers.get('location')
      if (!location || redirectCount >= 5) {
        return response
      }

      const nextUrl = new URL(location, url).toString()
      const nextOptions: RequestInit = {
        ...options,
        headers: mergeHeaders(options.headers),
      }

      if (response.status === 303) {
        nextOptions.method = 'GET'
        delete nextOptions.body
      }

      return handleProxyRequest(nextUrl, nextOptions, redirectCount + 1)
    }

    return response
  } catch (error: any) {
    console.error('Proxy request error:', error)

    // Handle timeout errors
    if (error.name === 'AbortError') {
      return new Response(
        JSON.stringify({ error: 'Request timeout', detail: 'Backend server did not respond in time' }),
        { status: 504, headers: { 'Content-Type': 'application/json' } }
      )
    }
    
    // Handle connection errors
    if (error.code === 'ECONNREFUSED') {
      return new Response(
        JSON.stringify({ error: 'Backend unavailable', detail: 'Cannot connect to backend server' }),
        { status: 503, headers: { 'Content-Type': 'application/json' } }
      )
    }
    
    // Generic error response
    return new Response(
      JSON.stringify({ error: 'Proxy error', detail: error.message }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    )
  }
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path: pathSegments } = await params
  const path = pathSegments.join('/')
  const url = `${BACKEND_URL}/${path}${request.nextUrl.search}`

  // Get cookie header from request
  const cookieHeader = request.headers.get('cookie')

  const response = await handleProxyRequest(url, {
    headers: {
      ...Object.fromEntries(request.headers.entries()),
      host: new URL(BACKEND_URL).host,
      ...(cookieHeader && { cookie: cookieHeader }),
    },
    credentials: 'include',
  })
  
  const data = await response.text()
  
  // Create response
  const proxyResponse = new NextResponse(data, {
    status: response.status,
    headers: {
      'Content-Type': response.headers.get('Content-Type') || 'application/json',
    },
  })
  
  // Forward Set-Cookie headers from backend to client
  const setCookieHeaders = response.headers.getSetCookie()
  setCookieHeaders.forEach(cookie => {
    proxyResponse.headers.append('Set-Cookie', cookie)
  })
  
  return proxyResponse
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path: pathSegments } = await params
  const path = pathSegments.join('/')
  const url = `${BACKEND_URL}/${path}`
  

  // Handle different content types
  let body: any
  const contentType = request.headers.get('content-type')

  // Only parse body if content-length > 0 or if there's actually a body
  const contentLength = request.headers.get('content-length')
  const hasBody = contentLength && parseInt(contentLength) > 0

  if (hasBody) {
    if (contentType?.includes('application/json')) {
      body = await request.json()
    } else if (contentType?.includes('text/plain')) {
      body = await request.text()
    } else {
      body = await request.text()
    }
  } else {
    body = undefined
  }
  
  console.log('Proxy POST to:', url)
  
  const forwardHeaders: Record<string, string> = {}
  request.headers.forEach((value, key) => {
    const lower = key.toLowerCase()
    if (lower === 'content-length' || lower === 'connection' || lower === 'host') {
      return
    }
    forwardHeaders[key] = value
  })

  forwardHeaders['content-type'] = contentType || 'application/json'

  if (!forwardHeaders['accept']) {
    forwardHeaders['accept'] = 'application/json'
  }

  const response = await handleProxyRequest(url, {
    method: 'POST',
    headers: forwardHeaders,
    body: body === undefined ? undefined : (typeof body === 'string' ? body : JSON.stringify(body)),
    credentials: 'include',
  })
  
  // Handle streaming responses (SSE)
  if (response.headers.get('content-type')?.includes('text/event-stream')) {
    // Create streaming response
    const streamingResponse = new NextResponse(response.body, {
      status: response.status,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no',
      },
    })
    
    // Forward Set-Cookie headers from backend to client
    const setCookieHeaders = response.headers.getSetCookie()
    setCookieHeaders.forEach(cookie => {
      streamingResponse.headers.append('Set-Cookie', cookie)
    })
    
    return streamingResponse
  }
  
  const data = await response.text()
  
  // Create response
  const proxyResponse = new NextResponse(data, {
    status: response.status,
    headers: {
      'Content-Type': response.headers.get('Content-Type') || 'application/json',
    },
  })
  
  // Forward Set-Cookie headers from backend to client
  const setCookieHeaders = response.headers.getSetCookie()
  setCookieHeaders.forEach(cookie => {
    proxyResponse.headers.append('Set-Cookie', cookie)
  })
  
  return proxyResponse
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path: pathSegments } = await params
  const path = pathSegments.join('/')
  const url = `${BACKEND_URL}/${path}`
  

  const body = await request.json()
  
  const contentType = request.headers.get('content-type') || 'application/json'

  const forwardHeaders: Record<string, string> = {}
  request.headers.forEach((value, key) => {
    const lower = key.toLowerCase()
    if (lower === 'content-length' || lower === 'connection' || lower === 'host') {
      return
    }
    forwardHeaders[key] = value
  })

  forwardHeaders['content-type'] = contentType

  if (!forwardHeaders['accept']) {
    forwardHeaders['accept'] = 'application/json'
  }

  const response = await handleProxyRequest(url, {
    method: 'PUT',
    headers: forwardHeaders,
    body: typeof body === 'string' ? body : JSON.stringify(body),
    credentials: 'include',
  })
  
  const data = await response.text()
  
  const proxyResponse = new NextResponse(data, {
    status: response.status,
    headers: {
      'Content-Type': response.headers.get('Content-Type') || 'application/json',
    },
  })
  
  // Forward Set-Cookie headers
  const setCookieHeaders = response.headers.getSetCookie()
  setCookieHeaders.forEach(cookie => {
    proxyResponse.headers.append('Set-Cookie', cookie)
  })
  
  return proxyResponse
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path: pathSegments } = await params
  const path = pathSegments.join('/')
  const url = `${BACKEND_URL}/${path}`


  const body = await request.json()

  const contentType = request.headers.get('content-type') || 'application/json'

  const forwardHeaders: Record<string, string> = {}
  request.headers.forEach((value, key) => {
    const lower = key.toLowerCase()
    if (lower === 'content-length' || lower === 'connection' || lower === 'host') {
      return
    }
    forwardHeaders[key] = value
  })

  forwardHeaders['content-type'] = contentType

  if (!forwardHeaders['accept']) {
    forwardHeaders['accept'] = 'application/json'
  }

  const response = await handleProxyRequest(url, {
    method: 'PATCH',
    headers: forwardHeaders,
    body: typeof body === 'string' ? body : JSON.stringify(body),
    credentials: 'include',
  })

  const data = await response.text()

  const proxyResponse = new NextResponse(data, {
    status: response.status,
    headers: {
      'Content-Type': response.headers.get('Content-Type') || 'application/json',
    },
  })

  // Forward Set-Cookie headers
  const setCookieHeaders = response.headers.getSetCookie()
  setCookieHeaders.forEach(cookie => {
    proxyResponse.headers.append('Set-Cookie', cookie)
  })

  return proxyResponse
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path: pathSegments } = await params
  const path = pathSegments.join('/')
  const url = `${BACKEND_URL}/${path}`



  const forwardHeaders: Record<string, string> = {}
  request.headers.forEach((value, key) => {
    const lower = key.toLowerCase()
    if (lower === 'content-length' || lower === 'connection' || lower === 'host') {
      return
    }
    forwardHeaders[key] = value
  })

  const response = await handleProxyRequest(url, {
    method: 'DELETE',
    headers: forwardHeaders,
    credentials: 'include',
  })

  const data = await response.text()

  const proxyResponse = new NextResponse(data, {
    status: response.status,
    headers: {
      'Content-Type': response.headers.get('Content-Type') || 'application/json',
    },
  })

  // Forward Set-Cookie headers
  const setCookieHeaders = response.headers.getSetCookie()
  setCookieHeaders.forEach(cookie => {
    proxyResponse.headers.append('Set-Cookie', cookie)
  })

  return proxyResponse
}

export async function OPTIONS() {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': 'http://localhost:3005',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
      'Access-Control-Allow-Credentials': 'true',
    },
  })
}
