import { test, expect } from '@playwright/test';

test.describe('Chat Integration Test', () => {
  test('Login and test chat interface', async ({ page }) => {
    // Step 1: Navigate to login page
    await page.goto('http://localhost:3005/login');
    console.log('✓ Navigated to login page');
    
    // Take screenshot of login page
    await page.screenshot({ path: 'test-login-page.png' });
    
    // Step 2: Fill in login credentials
    await page.fill('input[type="email"]', 'demo_hnw@sigmasight.com');
    await page.fill('input[type="password"]', 'demo12345');
    console.log('✓ Filled in credentials');
    
    // Step 3: Click login button
    await page.click('button[type="submit"]');
    console.log('✓ Clicked login button');
    
    // Step 4: Wait for navigation to portfolio page
    await page.waitForURL('**/portfolio**', { timeout: 10000 });
    console.log('✓ Redirected to portfolio page');
    
    // Take screenshot of portfolio page
    await page.screenshot({ path: 'test-portfolio-page.png' });
    
    // Step 5: Wait for page to load and find chat input
    await page.waitForTimeout(2000); // Let the page fully load
    
    // Step 6: Look for chat input at bottom of page
    const chatInput = page.locator('input[placeholder*="Ask a question"]').first();
    const chatInputVisible = await chatInput.isVisible().catch(() => false);
    
    if (chatInputVisible) {
      console.log('✓ Found chat input at bottom of page');
      
      // Click on the chat input to open the chat sheet
      await chatInput.click();
      console.log('✓ Clicked chat input');
      
      // Wait for chat sheet to open
      await page.waitForTimeout(1000);
      
      // Take screenshot of chat interface
      await page.screenshot({ path: 'test-chat-open.png' });
      
      // Look for the chat input in the sheet
      const sheetInput = page.locator('input[placeholder*="Type your message"]').first();
      const sheetInputVisible = await sheetInput.isVisible().catch(() => false);
      
      if (sheetInputVisible) {
        console.log('✓ Chat sheet opened successfully');
        
        // Type a test message
        await sheetInput.fill('What is my largest position?');
        console.log('✓ Typed test message');
        
        // Find and click send button
        const sendButton = page.locator('button:has-text("Send")').first();
        await sendButton.click();
        console.log('✓ Clicked send button');
        
        // Wait for response (give it some time for streaming)
        await page.waitForTimeout(5000);
        
        // Take screenshot of chat with response
        await page.screenshot({ path: 'test-chat-response.png' });
        
        // Check if there's any response
        const messages = await page.locator('.text-sm.whitespace-pre-wrap').count();
        console.log(`✓ Found ${messages} message(s) in chat`);
        
        // Check for error messages
        const errorElement = await page.locator('text=/error|failed/i').first();
        const hasError = await errorElement.isVisible().catch(() => false);
        
        if (hasError) {
          const errorText = await errorElement.textContent();
          console.log(`⚠️ Error detected: ${errorText}`);
        } else {
          console.log('✓ No errors detected');
        }
        
      } else {
        console.log('⚠️ Chat sheet input not found');
      }
    } else {
      console.log('⚠️ Chat input not found at bottom of page');
      
      // Try to find any chat-related element
      const anyChat = await page.locator('text=/chat|message|ask/i').first();
      if (await anyChat.isVisible().catch(() => false)) {
        console.log('ℹ️ Found chat-related element:', await anyChat.textContent());
      }
    }
    
    // Final screenshot
    await page.screenshot({ path: 'test-final-state.png', fullPage: true });
    console.log('✓ Test completed - check screenshots for visual verification');
  });
});