import { NextRequest, NextResponse } from 'next/server'

// Use environment variable or detect Docker environment
const BACKEND_URL = process.env.BACKEND_URL || 
  (process.env.DOCKER_ENV === 'true' ? 'http://host.docker.internal:8000' : 'http://localhost:8000')
const PROXY_TIMEOUT = 30000 // 30 seconds

console.log('Proxy Backend URL:', BACKEND_URL)
console.log('Docker Environment:', process.env.DOCKER_ENV)

/**
 * Enhanced proxy to handle cookie-based authentication
 * Forwards cookies in both directions for HttpOnly cookie support
 * Includes error handling and timeout management
 */

async function handleProxyRequest(
  url: string,
  options: RequestInit
): Promise<Response> {
  try {
    // Create AbortController for timeout
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), PROXY_TIMEOUT)
    
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    })
    
    clearTimeout(timeoutId)
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
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join('/')
  const url = `${BACKEND_URL}/${path}${request.nextUrl.search}`
  
  // Forward cookies from client to backend
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
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join('/')
  const url = `${BACKEND_URL}/${path}`
  
  // Forward cookies from client to backend
  const cookieHeader = request.headers.get('cookie')
  
  // Handle different content types
  let body: any
  const contentType = request.headers.get('content-type')
  
  if (contentType?.includes('application/json')) {
    body = await request.json()
  } else if (contentType?.includes('text/plain')) {
    body = await request.text()
  } else {
    body = await request.text()
  }
  
  console.log('Proxy POST to:', url)
  
  const response = await handleProxyRequest(url, {
    method: 'POST',
    headers: {
      'Content-Type': contentType || 'application/json',
      'Accept': request.headers.get('accept') || 'application/json',
      ...(cookieHeader && { cookie: cookieHeader }),
    },
    body: typeof body === 'string' ? body : JSON.stringify(body),
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
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join('/')
  const url = `${BACKEND_URL}/${path}`
  
  const cookieHeader = request.headers.get('cookie')
  const body = await request.json()
  
  const response = await handleProxyRequest(url, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      ...(cookieHeader && { cookie: cookieHeader }),
    },
    body: JSON.stringify(body),
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
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join('/')
  const url = `${BACKEND_URL}/${path}`
  
  const cookieHeader = request.headers.get('cookie')
  
  const response = await handleProxyRequest(url, {
    method: 'DELETE',
    headers: {
      ...(cookieHeader && { cookie: cookieHeader }),
    },
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
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
      'Access-Control-Allow-Credentials': 'true',
    },
  })
}