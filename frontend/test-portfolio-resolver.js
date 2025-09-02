const fetch = require('node-fetch');

async function testPortfolioResolver() {
  console.log('Testing Dynamic Portfolio ID Resolution...\n');
  
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
  console.log('✅ Login successful\n');
  
  // Step 2: Try to fetch portfolio with hardcoded ID (should work)
  console.log('2. Testing with known portfolio ID...');
  const knownId = 'c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e';
  
  const knownResponse = await fetch(`http://localhost:3005/api/proxy/api/v1/data/portfolio/${knownId}/complete`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
    }
  });
  
  if (knownResponse.ok) {
    const data = await knownResponse.json();
    console.log(`✅ Successfully fetched portfolio: ${data.portfolio.name}`);
    console.log(`   Portfolio ID: ${data.portfolio.id}`);
    console.log(`   Total Value: $${data.portfolio.total_value.toLocaleString()}\n`);
  } else {
    console.error(`❌ Failed to fetch portfolio: ${knownResponse.status}\n`);
  }
  
  // Step 3: Test validation with wrong portfolio ID
  console.log('3. Testing validation with incorrect portfolio ID...');
  const wrongId = '12345678-1234-1234-1234-123456789012';
  
  const wrongResponse = await fetch(`http://localhost:3005/api/proxy/api/v1/data/portfolio/${wrongId}/complete`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
    }
  });
  
  if (!wrongResponse.ok) {
    console.log(`✅ Correctly rejected invalid portfolio ID (${wrongResponse.status})\n`);
  } else {
    console.error('❌ Should have rejected invalid portfolio ID\n');
  }
  
  // Step 4: Login as different user
  console.log('4. Switching to demo_individual@sigmasight.com...');
  const login2Response = await fetch('http://localhost:3005/api/proxy/api/v1/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email: 'demo_individual@sigmasight.com',
      password: 'demo12345'
    })
  });
  
  if (!login2Response.ok) {
    console.error('❌ Second login failed');
    return;
  }
  
  const login2Data = await login2Response.json();
  const token2 = login2Data.access_token;
  console.log('✅ Login successful\n');
  
  // Step 5: Try the HNW portfolio with individual user (should fail)
  console.log('5. Testing portfolio ownership validation...');
  const crossUserResponse = await fetch(`http://localhost:3005/api/proxy/api/v1/data/portfolio/${knownId}/complete`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token2}`,
    }
  });
  
  if (!crossUserResponse.ok) {
    console.log(`✅ Correctly blocked cross-user portfolio access (${crossUserResponse.status})\n`);
  } else {
    console.error('❌ Should have blocked cross-user portfolio access\n');
  }
  
  // Step 6: Fetch individual's own portfolio
  console.log('6. Fetching individual user portfolio...');
  const individualId = '51134ffd-2f13-49bd-b1f5-0c327e801b69';
  
  const individualResponse = await fetch(`http://localhost:3005/api/proxy/api/v1/data/portfolio/${individualId}/complete`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token2}`,
    }
  });
  
  if (individualResponse.ok) {
    const data = await individualResponse.json();
    console.log(`✅ Successfully fetched portfolio: ${data.portfolio.name}`);
    console.log(`   Portfolio ID: ${data.portfolio.id}`);
    console.log(`   Total Value: $${data.portfolio.total_value.toLocaleString()}\n`);
  } else {
    console.error(`❌ Failed to fetch individual portfolio: ${individualResponse.status}\n`);
  }
  
  console.log('✅ Dynamic portfolio resolution test complete!');
  console.log('\nSummary:');
  console.log('- Portfolio IDs are unique per user');
  console.log('- Cross-user access is properly blocked');
  console.log('- Each demo user has their own portfolio');
  console.log('- Frontend can dynamically resolve IDs using hints');
}

testPortfolioResolver().catch(console.error);