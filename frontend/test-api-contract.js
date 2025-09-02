const fetch = require('node-fetch');

async function testAPIContract() {
  console.log('Testing API Contract Alignment...\n');
  
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
  
  // Extract cookies from login response
  const cookies = loginResponse.headers.raw()['set-cookie'] || [];
  const cookieString = cookies.join('; ');
  console.log('✅ Login successful, got token');
  console.log('   Cookies:', cookies.length > 0 ? 'Present' : 'None');
  
  // Step 2: Create conversation
  console.log('\n2. Creating conversation...');
  const convResponse = await fetch('http://localhost:3005/api/proxy/api/v1/chat/conversations', {
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
  
  if (!convResponse.ok) {
    console.error('❌ Failed to create conversation:', convResponse.status);
    const error = await convResponse.text();
    console.error(error);
    return;
  }
  
  const convData = await convResponse.json();
  const conversationId = convData.id || convData.conversation_id;
  console.log(`✅ Created conversation: ${conversationId}\n`);
  
  // Step 3: Send message with correct field names
  console.log('3. Sending message with correct API contract...');
  console.log('   Payload: { text: "...", conversation_id: "..." }');
  
  const messageResponse = await fetch('http://localhost:3005/api/proxy/api/v1/chat/send', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      'Cookie': cookieString
    },
    body: JSON.stringify({
      text: 'What is my largest position?',  // Backend expects 'text' not 'message'
      conversation_id: conversationId         // Include conversation_id
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
  
  console.log('\n4. Reading SSE stream...');
  
  for await (const chunk of reader) {
    buffer += decoder.decode(chunk, { stream: true });
    const lines = buffer.split('\n');
    
    for (let i = 0; i < lines.length - 1; i++) {
      const line = lines[i].trim();
      if (line.startsWith('event:')) {
        eventCount++;
        console.log(`   Event ${eventCount}: ${line}`);
        if (eventCount >= 5) {
          console.log('   ... (stopping after 5 events)');
          return;
        }
      }
    }
    
    buffer = lines[lines.length - 1];
  }
  
  console.log('\n✅ API Contract test complete!');
}

testAPIContract().catch(console.error);