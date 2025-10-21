/**
 * OpenAI Proxy API Route - Chat Completions
 *
 * Proxies OpenAI chat completions API requests to avoid CORS issues.
 * This matches the OpenAI SDK's expected path: /chat/completions
 */

import { NextRequest, NextResponse } from 'next/server';

export const runtime = 'edge'; // Use edge runtime for better streaming performance

export async function POST(request: NextRequest) {
  try {
    // Get OpenAI API key from environment
    const apiKey = process.env.NEXT_PUBLIC_OPENAI_API_KEY;

    if (!apiKey) {
      return NextResponse.json(
        { error: 'OpenAI API key not configured' },
        { status: 500 }
      );
    }

    // Get request body from frontend
    const body = await request.json();

    // Forward request to OpenAI
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`,
      },
      body: JSON.stringify(body),
    });

    // Check if request was successful
    if (!response.ok) {
      const error = await response.json();
      return NextResponse.json(
        { error: error.error?.message || 'OpenAI API error' },
        { status: response.status }
      );
    }

    // If streaming, return the stream
    if (body.stream) {
      return new NextResponse(response.body, {
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
        },
      });
    }

    // If not streaming, return JSON response
    const data = await response.json();
    return NextResponse.json(data);

  } catch (error) {
    console.error('OpenAI proxy error:', error);
    return NextResponse.json(
      { error: 'Failed to proxy request to OpenAI' },
      { status: 500 }
    );
  }
}
