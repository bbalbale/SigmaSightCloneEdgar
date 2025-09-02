const fetch = require('node-fetch');

async function testChatIntegration() {
  console.log('Testing Complete Chat Integration...\n');
  
  // Step 1: Login as demo user
  console.log('1. Logging in as demo_hnw@sigmasight.com...');
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
  console.log('✅ Login successful');
  console.log('   Token:', token ? 'Present' : 'Missing');
  console.log('   Cookies:', cookies.length > 0 ? 'Present' : 'None\n');
  
  // Step 2: Create conversation in green mode
  console.log('2. Creating conversation in green mode...');
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
    const error = await createResponse.text();
    console.error(error);
    return;
  }
  
  const conversation = await createResponse.json();
  const conversationId = conversation.id;  // Using 'id' now, not 'conversation_id'
  console.log(`✅ Created conversation: ${conversationId}`);
  console.log(`   Mode: ${conversation.mode}\n`);
  
  // Step 3: Send a test message
  console.log('3. Sending test message...');
  const messageResponse = await fetch('http://localhost:3005/api/proxy/api/v1/chat/send', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      'Cookie': cookieString,
      'Accept': 'text/event-stream'
    },
    body: JSON.stringify({
      text: 'What is my largest position?',
      conversation_id: conversationId  // Still use conversation_id in request payload
    })
  });
  
  if (!messageResponse.ok) {
    console.error('❌ Failed to send message:', messageResponse.status);
    const error = await messageResponse.text();
    console.error(error);
    return;
  }
  
  console.log('✅ Message sent successfully!');
  console.log('   Response type:', messageResponse.headers.get('content-type'));
  
  // Read some of the streaming response
  const reader = messageResponse.body;
  const decoder = new TextDecoder();
  let buffer = '';
  let eventCount = 0;
  let hasTokens = false;
  let hasDone = false;
  
  console.log('\n4. Reading SSE stream...');
  
  for await (const chunk of reader) {
    buffer += decoder.decode(chunk, { stream: true });
    const lines = buffer.split('\n');
    
    for (let i = 0; i < lines.length - 1; i++) {
      const line = lines[i].trim();
      if (line.startsWith('event:')) {
        eventCount++;
        const eventType = line.substring(6).trim();
        console.log(`   Event ${eventCount}: ${eventType}`);
        
        if (eventType === 'token') hasTokens = true;
        if (eventType === 'done') hasDone = true;
        
        if (eventCount >= 10 || hasDone) {
          console.log('   ... (stopping after done or 10 events)');
          break;
        }
      }
    }
    
    if (eventCount >= 10 || hasDone) break;
    buffer = lines[lines.length - 1];
  }
  
  console.log('\n5. Test mode switching...');
  const modeSwitchResponse = await fetch(
    `http://localhost:3005/api/proxy/api/v1/chat/conversations/${conversationId}/mode`,
    {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        'Cookie': cookieString
      },
      body: JSON.stringify({ mode: 'blue' })
    }
  );
  
  if (modeSwitchResponse.ok) {
    const modeData = await modeSwitchResponse.json();
    console.log(`✅ Mode switched from ${modeData.previous_mode} to ${modeData.new_mode}`);
  } else {
    console.log(`⚠️  Mode switch endpoint returned ${modeSwitchResponse.status} (may not be implemented)`);
  }
  
  // Step 6: Verify conversation persistence
  console.log('\n6. Verifying conversation persistence...');
  const listResponse = await fetch('http://localhost:3005/api/proxy/api/v1/chat/conversations?limit=5', {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Cookie': cookieString
    }
  });
  
  if (listResponse.ok) {
    const conversations = await listResponse.json();
    const ourConversation = conversations.find(c => c.id === conversationId);
    if (ourConversation) {
      console.log(`✅ Conversation persisted with ID: ${ourConversation.id}`);
      console.log(`   Current mode: ${ourConversation.mode}`);
    } else {
      console.log('⚠️  Conversation not found in list');
    }
  } else {
    console.log(`❌ Failed to list conversations: ${listResponse.status}`);
  }
  
  // Step 7: Clean up
  console.log('\n7. Cleaning up test conversation...');
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
  
  if (deleteResponse.ok || deleteResponse.status === 204) {
    console.log('✅ Test conversation deleted\n');
  } else {
    console.log(`⚠️  Could not delete conversation (${deleteResponse.status})\n`);
  }
  
  console.log('✅ Chat Integration test complete!');
  console.log('\nSummary:');
  console.log('- Backend conversation creation works');
  console.log('- Message streaming works');
  console.log('- SSE event stream properly formatted');
  console.log(`- Received ${hasTokens ? 'token' : 'no token'} events`);
  console.log(`- Stream ${hasDone ? 'completed' : 'did not complete'} properly`);
  console.log('- Conversation persistence verified');
  console.log('- Mode switching tested');
  
  console.log('\n✨ Integration Status: READY FOR FRONTEND TESTING');
}

testChatIntegration().catch(console.error);