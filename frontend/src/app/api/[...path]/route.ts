import { type NextRequest, NextResponse } from "next/server";

const API_URL = process.env.API_URL || "http://localhost:8000";

async function proxyRequest(
  request: NextRequest,
  path: string
): Promise<NextResponse> {
  const url = `${API_URL}/api/${path}`;

  // Forward the request with headers
  const headers = new Headers();

  // Copy relevant headers from the request
  const headersToForward = [
    "content-type",
    "accept",
    "authorization",
    "x-requested-with",
  ];
  for (const header of headersToForward) {
    const value = request.headers.get(header);
    if (value) {
      headers.set(header, value);
    }
  }

  // Get cookies and forward them
  const cookies = request.cookies.getAll();
  const cookieHeader = cookies.map((c) => `${c.name}=${c.value}`).join("; ");

  // Debug logging
  console.log(`[API Proxy] ${request.method} ${url}`);
  console.log(`[API Proxy] Cookies found: ${cookies.length}`, cookies.map(c => c.name));

  if (cookieHeader) {
    headers.set("Cookie", cookieHeader);
  }

  // Prepare fetch options
  const fetchOptions: RequestInit & { duplex?: string } = {
    method: request.method,
    headers,
  };

  // Forward body for methods that have one
  if (request.method !== "GET" && request.method !== "HEAD") {
    fetchOptions.body = request.body;
    fetchOptions.duplex = "half";
  }

  try {
    const response = await fetch(url, fetchOptions);

    // Create response with body
    const responseBody = response.body;
    const responseHeaders = new Headers();

    // Forward response headers
    response.headers.forEach((value, key) => {
      // Forward Set-Cookie headers to set cookies in the browser
      if (key.toLowerCase() === "set-cookie") {
        responseHeaders.append(key, value);
      } else {
        responseHeaders.set(key, value);
      }
    });

    return new NextResponse(responseBody, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error("[API Proxy] Error:", error);
    return NextResponse.json(
      { error: "Failed to connect to backend" },
      { status: 502 }
    );
  }
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
): Promise<NextResponse> {
  const { path } = await params;
  return proxyRequest(request, path.join("/"));
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
): Promise<NextResponse> {
  const { path } = await params;
  return proxyRequest(request, path.join("/"));
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
): Promise<NextResponse> {
  const { path } = await params;
  return proxyRequest(request, path.join("/"));
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
): Promise<NextResponse> {
  const { path } = await params;
  return proxyRequest(request, path.join("/"));
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
): Promise<NextResponse> {
  const { path } = await params;
  return proxyRequest(request, path.join("/"));
}
