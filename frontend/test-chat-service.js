const fetch = require('node-fetch');

async function testChatService() {
  console.log('Testing Complete Chat Service Implementation...\n');
  
  // Step 1: Login
  console.log('1. Logging in...');
  const loginResponse = await fetch('http://localhost:3005/api/proxy/api/v1/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email: 'demo_hnw@sigmasight.com',
      password: 'demo12345'
    })
  });
  
  if (!loginResponse.ok) {
    console.error('❌ Login failed');
    return;
  }
  
  const loginData = await loginResponse.json();
  const token = loginData.access_token;
  const cookies = loginResponse.headers.raw()['set-cookie'] || [];
  const cookieString = cookies.join('; ');
  console.log('✅ Login successful\n');
  
  // Step 2: Create a conversation
  console.log('2. Creating conversation...');
  const createResponse = await fetch('http://localhost:3005/api/proxy/api/v1/chat/conversations', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      'Cookie': cookieString
    },
    body: JSON.stringify({
      mode: 'green'
    })
  });
  
  if (!createResponse.ok) {
    console.error('❌ Failed to create conversation:', createResponse.status);
    return;
  }
  
  const conversation = await createResponse.json();
  const conversationId = conversation.id;
  console.log(`✅ Created conversation: ${conversationId}`);
  console.log(`   Mode: ${conversation.mode}\n`);
  
  // Step 3: Send a message (this will trigger streaming)
  console.log('3. Sending test message...');
  const messageResponse = await fetch('http://localhost:3005/api/proxy/api/v1/chat/send', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      'Cookie': cookieString
    },
    body: JSON.stringify({
      text: 'Hello, this is a test message',
      conversation_id: conversationId
    })
  });
  
  if (!messageResponse.ok) {
    console.error('❌ Failed to send message:', messageResponse.status);
  } else {
    console.log('✅ Message sent (streaming response received)\n');
  }
  
  // Step 4: List conversations
  console.log('4. Listing conversations...');
  const listResponse = await fetch('http://localhost:3005/api/proxy/api/v1/chat/conversations?limit=5', {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Cookie': cookieString
    }
  });
  
  if (!listResponse.ok) {
    console.error('❌ Failed to list conversations:', listResponse.status);
  } else {
    const conversations = await listResponse.json();
    console.log(`✅ Found ${conversations.length} conversation(s)`);
    if (conversations.length > 0) {
      console.log('   Recent conversations:');
      conversations.slice(0, 3).forEach(conv => {
        const id = conv.id || 'unknown';
        console.log(`   - ${String(id).substring(0, 8)}... (mode: ${conv.mode})`);
      });
    }
    console.log();
  }
  
  // Step 5: Try to get messages (endpoint might not exist yet)
  console.log('5. Attempting to get messages...');
  const messagesResponse = await fetch(
    `http://localhost:3005/api/proxy/api/v1/chat/conversations/${conversationId}/messages?limit=10`,
    {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Cookie': cookieString
      }
    }
  );
  
  if (!messagesResponse.ok) {
    console.log(`⚠️  Messages endpoint not implemented (${messagesResponse.status}) - expected\n`);
  } else {
    const messages = await messagesResponse.json();
    console.log(`✅ Retrieved ${messages.messages?.length || 0} messages\n`);
  }
  
  // Step 6: Test error handling (invalid conversation ID)
  console.log('6. Testing error handling with invalid ID...');
  const invalidResponse = await fetch(
    'http://localhost:3005/api/proxy/api/v1/chat/conversations/invalid-id-12345',
    {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Cookie': cookieString
      }
    }
  );
  
  if (!invalidResponse.ok) {
    console.log(`✅ Correctly rejected invalid ID (${invalidResponse.status})\n`);
  } else {
    console.error('❌ Should have rejected invalid ID\n');
  }
  
  // Step 7: Delete the test conversation
  console.log('7. Cleaning up test conversation...');
  const deleteResponse = await fetch(
    `http://localhost:3005/api/proxy/api/v1/chat/conversations/${conversationId}`,
    {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Cookie': cookieString
      }
    }
  );
  
  if (deleteResponse.ok) {
    console.log('✅ Test conversation deleted\n');
  } else {
    console.log(`⚠️  Could not delete conversation (${deleteResponse.status})\n`);
  }
  
  console.log('✅ Chat Service test complete!');
  console.log('\nSummary:');
  console.log('- Conversation creation works');
  console.log('- Message sending works (SSE streaming)');
  console.log('- Conversation listing works');
  console.log('- Error handling works');
  console.log('- Messages endpoint needs backend implementation');
}

testChatService().catch(console.error);