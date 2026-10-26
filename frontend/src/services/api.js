/**
 * api.js
 * 
 * HTTP client for communicating with the FastAPI backend.
 * Uses VITE_API_URL environment variable when set, otherwise falls back
 * to relative URLs (leveraging the Vite dev server proxy).
 */

const BASE_URL = import.meta.env.VITE_API_URL || '';

async function handleResponse(response) {
  if (!response.ok) {
    let errorMsg = `HTTP Error ${response.status}: ${response.statusText}`;
    try {
      const errorJson = await response.json();
      if (errorJson.detail) {
        errorMsg = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
      }
    } catch {
      // ignore json parse error
    }
    throw new Error(errorMsg);
  }
  return response.json();
}

export async function fetchConfig() {
  const res = await fetch(`${BASE_URL}/api/config`);
  return handleResponse(res);
}

export async function fetchForecast(day, cutoff = '09:00') {
  const params = new URLSearchParams({ day, cutoff });
  const res = await fetch(`${BASE_URL}/api/forecast?${params.toString()}`);
  return handleResponse(res);
}

export async function fetchMetrics(cutoff = '09:00') {
  const params = new URLSearchParams({ cutoff });
  const res = await fetch(`${BASE_URL}/api/metrics?${params.toString()}`);
  return handleResponse(res);
}

export async function fetchHourlyMetrics(cutoff = '09:00') {
  const params = new URLSearchParams({ cutoff });
  const res = await fetch(`${BASE_URL}/api/metrics/by-hour?${params.toString()}`);
  return handleResponse(res);
}
