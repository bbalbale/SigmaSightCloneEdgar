import { useChatStore } from '@/stores/chatStore'
import { chatService } from '@/services/chatService'

class ChatManager {
  private static instance: ChatManager | null = null
  private currentMessageHandler: ((text: string) => void) | null = null

  static getInstance(): ChatManager {
    if (!ChatManager.instance) {
      ChatManager.instance = new ChatManager()
    }
    return ChatManager.instance
  }

  setMessageHandler(handler: (text: string) => void) {
    this.currentMessageHandler = handler
  }

  async sendMessage(text: string) {
    const store = useChatStore.getState()
    
    // Open the chat sheet
    store.setOpen(true)
    
    // If we have a handler (from the ChatInterface component), use it
    // Otherwise, just open the sheet and the user can type the message again
    if (this.currentMessageHandler) {
      // Small delay to ensure sheet is open
      setTimeout(() => {
        this.currentMessageHandler?.(text)
      }, 100)
    }
  }

  openChat() {
    useChatStore.getState().setOpen(true)
  }
}

export const chatManager = ChatManager.getInstance()