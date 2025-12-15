/**
 * Feedback Service - Submit ratings for AI messages
 *
 * Allows users to provide thumbs up/down feedback on assistant responses.
 * Used for offline analysis and knowledge base improvement.
 */

import { apiClient } from './apiClient'

export interface FeedbackData {
  rating: 'up' | 'down'
  edited_text?: string
  comment?: string
}

export interface FeedbackResponse {
  id: string
  message_id: string
  rating: 'up' | 'down'
  edited_text?: string
  comment?: string
}

/**
 * Submit feedback on an AI message
 *
 * @param messageId - Backend message UUID
 * @param feedback - Feedback data (rating, optional edited_text, optional comment)
 * @returns Created/updated feedback record
 */
export async function submitFeedback(
  messageId: string,
  feedback: FeedbackData
): Promise<FeedbackResponse> {
  const response = await apiClient.post<FeedbackResponse>(
    `/api/v1/chat/messages/${messageId}/feedback`,
    feedback
  )
  return response
}

/**
 * Get feedback for a message (if any)
 *
 * @param messageId - Backend message UUID
 * @returns Feedback record or null if none exists
 */
export async function getFeedback(messageId: string): Promise<FeedbackResponse | null> {
  try {
    const response = await apiClient.get<FeedbackResponse>(
      `/api/v1/chat/messages/${messageId}/feedback`
    )
    return response
  } catch (error: unknown) {
    // Return null if no feedback exists (404)
    if (error && typeof error === 'object' && 'status' in error && error.status === 404) {
      return null
    }
    throw error
  }
}

/**
 * Delete feedback for a message
 *
 * @param messageId - Backend message UUID
 */
export async function deleteFeedback(messageId: string): Promise<void> {
  await apiClient.delete(`/api/v1/chat/messages/${messageId}/feedback`)
}

export default {
  submitFeedback,
  getFeedback,
  deleteFeedback,
}
