/**
 * All HTTP calls to the FastAPI backend live here (Section 53) — no
 * component should call fetch() directly.
 *
 * BASE resolves two different deployment shapes:
 *   - Local dev / same-origin production (a reverse proxy forwards
 *     /api to the backend): the default "/api" works as-is, matching
 *     vite.config.js's dev proxy.
 *   - Split-origin production (frontend on Vercel/Netlify, backend on
 *     Render/Railway as its own domain): set VITE_API_BASE_URL at build
 *     time to the backend's full URL (e.g. https://collegepath-api.onrender.com),
 *     and CORS_ORIGINS on the backend must include the frontend's exact
 *     origin (see docs/deployment.md) — without both changes, requests
 *     would either 404 (wrong host) or be blocked by the browser (CORS).
 */
const BASE = import.meta.env.VITE_API_BASE_URL || "/api";

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function parseErrorDetail(response) {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail) && body.detail[0]?.msg) {
      return body.detail[0].msg;
    }
  } catch {
    // response wasn't JSON — fall through to a generic message
  }
  return "Something went wrong on the server.";
}

/**
 * POST /chat. Throws ApiError with a user-safe message on any non-2xx
 * response, and a distinct network-failure message if the request never
 * reached the server at all (Section 35).
 */
export async function sendMessage(message) {
  let response;
  try {
    response = await fetch(`${BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
  } catch {
    throw new ApiError(
      "I couldn't connect to CollegePath AI right now. Please check your connection and try again.",
      0
    );
  }

  if (!response.ok) {
    const detail = await parseErrorDetail(response);
    throw new ApiError(detail, response.status);
  }

  return response.json();
}

/** GET /categories. Returns [] on failure rather than throwing — category
 * chips are a nice-to-have, not worth blocking the whole UI over. */
export async function getCategories() {
  try {
    const response = await fetch(`${BASE}/categories`);
    if (!response.ok) return [];
    const data = await response.json();
    return data.categories ?? [];
  } catch {
    return [];
  }
}

/** GET /health. Used only for the header's online/offline indicator. */
export async function checkHealth() {
  try {
    const response = await fetch(`${BASE}/health`);
    return response.ok;
  } catch {
    return false;
  }
}

export { ApiError };
