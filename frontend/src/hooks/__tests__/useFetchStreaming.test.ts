import { renderHook, act } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'

import { useFetchStreaming } from '@/hooks/useFetchStreaming'
import { chatAuthService } from '@/services/chatAuthService'
import { useStreamStore } from '@/stores/streamStore'

// Helper to build SSE event strings
function sse(type: string, payload: any) {
  return `event: ${type}\n` + `data: ${JSON.stringify(payload)}\n\n`
}

function makeSSEStream(chunks: string[]) {
  const encoder = new TextEncoder()
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk))
      }
      controller.close()
    },
  })
}

describe('useFetchStreaming SSE behavior', () => {
  beforeEach(() => {
    // Reset zustand store to avoid cross-test contamination
    act(() => {
      useStreamStore.getState().reset()
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('falls back to backend final_text when no tokens after tool_result (continuation=0)', async () => {
    const runId = 'test-run-1'

    const toolResultEvt = {
      run_id: runId,
      seq: 1,
      type: 'tool_result',
      data: {
        tool_name: 'web_search',
        tool_result: { ok: true },
      },
      timestamp: Date.now(),
    }

    const doneEvt = {
      run_id: runId,
      seq: 2,
      type: 'done',
      data: {
        final_text: 'Backend final fallback',
        token_counts: { initial: 0, continuation: 0 },
        event_timeline: [
          { type: 'tool_result', t_ms: 100 },
          { type: 'done_emit', t_ms: 150 },
        ],
      },
      timestamp: Date.now(),
    }

    const stream = makeSSEStream([
      sse('tool_result', toolResultEvt),
      sse('done', doneEvt),
    ])

    const response = new Response(stream, {
      headers: { 'Content-Type': 'text/event-stream' },
      status: 200,
    })

    vi.spyOn(chatAuthService, 'authenticatedFetch').mockResolvedValue(response as any)

    const { result } = renderHook(() => useFetchStreaming())

    let finalText = ''
    const donePromise = new Promise<void>((resolve) => {
      // start stream
      act(() => {
        result.current.streamMessage('conv-1', 'hello', {
          onDone: (txt) => {
            finalText = txt
            resolve()
          },
        })
      })
    })

    await act(async () => {
      await donePromise
    })

    expect(finalText).toBe('Backend final fallback')
  })

  it('uses buffered streamed tokens when available and ignores backend final_text', async () => {
    const runId = 'test-run-2'

    const token1 = {
      run_id: runId,
      seq: 1,
      type: 'token',
      data: { delta: 'Hello' },
      timestamp: Date.now(),
    }
    const token2 = {
      run_id: runId,
      seq: 2,
      type: 'token',
      data: { delta: ' world' },
      timestamp: Date.now(),
    }
    const doneEvt = {
      run_id: runId,
      seq: 3,
      type: 'done',
      data: {
        final_text: 'Different text',
        token_counts: { initial: 2, continuation: 2 },
      },
      timestamp: Date.now(),
    }

    const stream = makeSSEStream([
      sse('token', token1),
      sse('token', token2),
      sse('done', doneEvt),
    ])

    const response = new Response(stream, {
      headers: { 'Content-Type': 'text/event-stream' },
      status: 200,
    })

    vi.spyOn(chatAuthService, 'authenticatedFetch').mockResolvedValue(response as any)

    const { result } = renderHook(() => useFetchStreaming())

    let finalText = ''
    const tokens: string[] = []
    const donePromise = new Promise<void>((resolve) => {
      act(() => {
        result.current.streamMessage('conv-1', 'hello', {
          onToken: (t) => tokens.push(t),
          onDone: (txt) => {
            finalText = txt
            resolve()
          },
        })
      })
    })

    await act(async () => {
      await donePromise
    })

    expect(tokens).toEqual(['Hello', ' world'])
    expect(finalText).toBe('Hello world')
  })

  it('surfaces info retry_scheduled with attempt and retry_in_ms', async () => {
    const runId = 'test-run-3'

    const infoEvt = {
      run_id: runId,
      seq: 0,
      type: 'info',
      data: {
        info_type: 'retry_scheduled',
        attempt: 2,
        max_attempts: 3,
        retry_in_ms: 750,
        retryable: true,
      },
      timestamp: Date.now(),
    }

    const doneEvt = {
      run_id: runId,
      seq: 1,
      type: 'done',
      data: {
        final_text: '',
        token_counts: { initial: 0, continuation: 0 },
      },
      timestamp: Date.now(),
    }

    const stream = makeSSEStream([
      sse('info', infoEvt),
      sse('done', doneEvt),
    ])

    const response = new Response(stream, {
      headers: { 'Content-Type': 'text/event-stream' },
      status: 200,
    })

    vi.spyOn(chatAuthService, 'authenticatedFetch').mockResolvedValue(response as any)

    const { result } = renderHook(() => useFetchStreaming())

    const seenInfos: any[] = []
    const donePromise = new Promise<void>((resolve) => {
      act(() => {
        result.current.streamMessage('conv-1', 'hello', {
          onInfo: (info) => {
            seenInfos.push(info)
          },
          onDone: () => resolve(),
        })
      })
    })

    await act(async () => {
      await donePromise
    })

    expect(seenInfos.length).toBe(1)
    expect(seenInfos[0].info_type).toBe('retry_scheduled')
    expect(seenInfos[0].attempt).toBe(2)
    expect(seenInfos[0].max_attempts).toBe(3)
    expect(seenInfos[0].retry_in_ms).toBe(750)
  })

  it('surfaces info model_switch with from/to models', async () => {
    const runId = 'test-run-4'

    const infoEvt = {
      run_id: runId,
      seq: 0,
      type: 'info',
      data: {
        info_type: 'model_switch',
        from: 'gpt-4o',
        to: 'gpt-4o-mini',
        attempt: 2,
      },
      timestamp: Date.now(),
    }

    const doneEvt = {
      run_id: runId,
      seq: 1,
      type: 'done',
      data: {
        final_text: 'ok',
        token_counts: { initial: 0, continuation: 0 },
      },
      timestamp: Date.now(),
    }

    const stream = makeSSEStream([
      sse('info', infoEvt),
      sse('done', doneEvt),
    ])

    const response = new Response(stream, {
      headers: { 'Content-Type': 'text/event-stream' },
      status: 200,
    })

    vi.spyOn(chatAuthService, 'authenticatedFetch').mockResolvedValue(response as any)

    const { result } = renderHook(() => useFetchStreaming())

    const infos: any[] = []
    const donePromise = new Promise<void>((resolve) => {
      act(() => {
        result.current.streamMessage('conv-1', 'hello', {
          onInfo: (info) => infos.push(info),
          onDone: () => resolve(),
        })
      })
    })

    await act(async () => {
      await donePromise
    })

    expect(infos.length).toBe(1)
    expect(infos[0].info_type).toBe('model_switch')
    expect(infos[0].from).toBe('gpt-4o')
    expect(infos[0].to).toBe('gpt-4o-mini')
    expect(infos[0].attempt).toBe(2)
  })
})
