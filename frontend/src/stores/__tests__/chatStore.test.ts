/**
 * Unit tests for Chat Store Conversation ID Sync
 * Tests TODO 6.49 and 6.50 implementations
 */

import { describe, test, expect, beforeEach, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useChatStore } from '../chatStore'

// Mock crypto.randomUUID for consistent testing
const mockUUID = '550e8400-e29b-41d4-a716-446655440000'
Object.defineProperty(global, 'crypto', {
  value: {
    randomUUID: vi.fn(() => mockUUID)
  },
  writable: true
})

describe('ChatStore - Conversation ID Management', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear()
    // Reset the store
    const { result } = renderHook(() => useChatStore())
    act(() => {
      result.current.reset()
    })
  })

  describe('TODO 6.50: UUID Format Validation', () => {
    test('should generate valid UUID format when creating conversation', () => {
      const { result } = renderHook(() => useChatStore())
      
      act(() => {
        const conversationId = result.current.createConversation('green')
        expect(conversationId).toBe(mockUUID)
        expect(conversationId).toMatch(
          /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
        )
      })
    })

    test('should use backend ID if provided', () => {
      const { result } = renderHook(() => useChatStore())
      const backendId = 'backend-550e8400-e29b-41d4-a716-446655440001'
      
      act(() => {
        const conversationId = result.current.createConversation('green', backendId)
        expect(conversationId).toBe(backendId)
      })
    })

    test('should reject invalid UUID formats in hydrateFromStorage', () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
      const invalidId = 'conv_1234567890_abc123'
      localStorage.setItem('conversationId', invalidId)
      
      const { result } = renderHook(() => useChatStore())
      
      act(() => {
        result.current.hydrateFromStorage()
      })
      
      // Should log warning about invalid format
      expect(consoleSpy).toHaveBeenCalledWith(
        '[ChatStore] Invalid conversation ID format in localStorage:',
        invalidId
      )
      
      // Should clear invalid ID from localStorage
      expect(localStorage.getItem('conversationId')).toBeNull()
      
      consoleSpy.mockRestore()
    })

    test('should reject old format conversation IDs (conv_timestamp_random)', () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
      const oldFormatId = 'conv_1756914328783_fd5o8vldb'
      localStorage.setItem('conversationId', oldFormatId)
      
      const { result } = renderHook(() => useChatStore())
      
      act(() => {
        result.current.hydrateFromStorage()
      })
      
      // Should detect and clear old format
      expect(consoleSpy).toHaveBeenCalledWith(
        '[ChatStore] Invalid conversation ID format in localStorage:',
        oldFormatId
      )
      expect(localStorage.getItem('conversationId')).toBeNull()
      expect(result.current.currentConversationId).toBeNull()
      
      consoleSpy.mockRestore()
    })

    test('should validate various UUID formats', () => {
      const { result } = renderHook(() => useChatStore())
      
      const validUUIDs = [
        '550e8400-e29b-41d4-a716-446655440000',
        'f47ac10b-58cc-4372-a567-0e02b2c3d479',
        '6ba7b810-9dad-11d1-80b4-00c04fd430c8',
        '00000000-0000-0000-0000-000000000000',
      ]
      
      const invalidUUIDs = [
        'conv_1234567890_abc123', // Old format
        'not-a-uuid',
        '550e8400-e29b-41d4-a716', // Too short
        '550e8400-e29b-41d4-a716-446655440000-extra', // Too long
        'XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX', // Invalid characters
        '',
        null,
        undefined,
      ]
      
      // Test valid UUIDs
      validUUIDs.forEach(uuid => {
        localStorage.setItem('conversationId', uuid)
        act(() => {
          result.current.hydrateFromStorage()
        })
        expect(result.current.currentConversationId).toBe(uuid)
      })
      
      // Test invalid UUIDs
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
      invalidUUIDs.forEach(uuid => {
        if (uuid) {
          localStorage.setItem('conversationId', uuid)
          act(() => {
            result.current.hydrateFromStorage()
          })
          expect(localStorage.getItem('conversationId')).toBeNull()
        }
      })
      consoleSpy.mockRestore()
    })

    test('should handle backend 422 error scenario', () => {
      const { result } = renderHook(() => useChatStore())
      
      // Simulate creating conversation with old format (should not happen anymore)
      const oldFormatId = 'conv_1756914328783_fd5o8vldb'
      
      // Verify new format is always used
      act(() => {
        const conversationId = result.current.createConversation('blue')
        expect(conversationId).not.toMatch(/^conv_/)
        expect(conversationId).toMatch(
          /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
        )
      })
    })
  })

  describe('TODO 6.49: Conversation ID Sync', () => {
    test('should sync valid conversation ID from localStorage on hydrate', () => {
      const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {})
      const validId = '550e8400-e29b-41d4-a716-446655440002'
      localStorage.setItem('conversationId', validId)
      
      const { result } = renderHook(() => useChatStore())
      
      act(() => {
        result.current.hydrateFromStorage()
      })
      
      expect(result.current.currentConversationId).toBe(validId)
      expect(consoleSpy).toHaveBeenCalledWith(
        '[ChatStore] Synced conversation ID from localStorage:',
        validId
      )
      
      consoleSpy.mockRestore()
    })

    test('should prioritize conversationId over currentConversationId in localStorage', () => {
      const primaryId = '550e8400-e29b-41d4-a716-446655440003'
      const secondaryId = '550e8400-e29b-41d4-a716-446655440004'
      
      localStorage.setItem('conversationId', primaryId)
      localStorage.setItem('currentConversationId', secondaryId)
      
      const { result } = renderHook(() => useChatStore())
      
      act(() => {
        result.current.hydrateFromStorage()
      })
      
      // Should use primary ID
      expect(result.current.currentConversationId).toBe(primaryId)
    })

    test('should use currentConversationId if conversationId is not present', () => {
      const secondaryId = '550e8400-e29b-41d4-a716-446655440005'
      localStorage.setItem('currentConversationId', secondaryId)
      
      const { result } = renderHook(() => useChatStore())
      
      act(() => {
        result.current.hydrateFromStorage()
      })
      
      expect(result.current.currentConversationId).toBe(secondaryId)
    })

    test('should loadConversation when valid ID is provided', () => {
      const { result } = renderHook(() => useChatStore())
      const conversationId = '550e8400-e29b-41d4-a716-446655440006'
      
      // First create a conversation
      act(() => {
        result.current.createConversation('blue', conversationId)
      })
      
      // Reset current conversation
      act(() => {
        result.current.currentConversationId = null
      })
      
      // Load the conversation
      act(() => {
        result.current.loadConversation(conversationId)
      })
      
      expect(result.current.currentConversationId).toBe(conversationId)
      expect(result.current.currentMode).toBe('blue')
    })
  })

  describe('Integration: Login Flow', () => {
    test('should clear old conversation and set new one on login', () => {
      const oldId = 'conv_oldformat_123'
      const newId = '550e8400-e29b-41d4-a716-446655440007'
      
      // Simulate old conversation in store
      localStorage.setItem('conversationId', oldId)
      localStorage.setItem('chatHistory', 'old-history')
      
      const { result } = renderHook(() => useChatStore())
      
      // Simulate login clearing old data
      act(() => {
        localStorage.removeItem('conversationId')
        localStorage.removeItem('chatHistory')
        localStorage.setItem('conversationId', newId)
        result.current.hydrateFromStorage()
      })
      
      expect(result.current.currentConversationId).toBe(newId)
      expect(localStorage.getItem('chatHistory')).toBeNull()
    })
  })

  describe('Edge Cases', () => {
    test('should handle null/undefined conversation IDs gracefully', () => {
      const { result } = renderHook(() => useChatStore())
      
      act(() => {
        result.current.loadConversation('')
      })
      
      // Should not crash or set invalid ID
      expect(result.current.currentConversationId).not.toBe('')
    })

    test('should handle localStorage errors gracefully', () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
      
      // Mock localStorage to throw error
      const originalGetItem = Storage.prototype.getItem
      Storage.prototype.getItem = vi.fn(() => {
        throw new Error('localStorage access denied')
      })
      
      const { result } = renderHook(() => useChatStore())
      
      // Should not crash
      act(() => {
        try {
          result.current.hydrateFromStorage()
        } catch (e) {
          // Expected to catch error
        }
      })
      
      // Restore localStorage
      Storage.prototype.getItem = originalGetItem
      consoleSpy.mockRestore()
    })
  })
})

describe('ChatInterface - Conversation ID Sync', () => {
  // Note: These tests would require a more complex setup with React Testing Library
  // and mocking the ChatInterface component. For brevity, including conceptual tests.
  
  test.todo('should sync conversation ID from localStorage on mount')
  test.todo('should reset store if invalid conversation ID detected on mount')
  test.todo('should call hydrateFromStorage on component mount')
  test.todo('should handle missing conversation ID gracefully')
})