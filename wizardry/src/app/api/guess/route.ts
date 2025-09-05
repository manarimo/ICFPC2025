import { NextRequest, NextResponse } from 'next/server';

const OFFICIAL_API_URL = 'https://31pwr5t6ij.execute-api.eu-west-2.amazonaws.com';
const MOCK_API_URL = process.env.ICFP_API_BASE_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const backendType = request.headers.get('x-backend-type') || 'mock';
    
    const apiBaseUrl = backendType === 'official' ? OFFICIAL_API_URL : MOCK_API_URL;
    
    const response = await fetch(`${apiBaseUrl}/guess`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();
    
    return NextResponse.json(data, { 
      status: response.status,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
      }
    });
  } catch (error) {
    console.error('Error proxying guess request:', error);
    return NextResponse.json(
      { error: 'Failed to proxy request' },
      { status: 500 }
    );
  }
}

export async function OPTIONS() {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
}