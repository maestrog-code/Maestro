export type HealthResponse = {
  status: 'ok' | 'error'
  database: 'ok' | 'error'
  redis: 'ok' | 'error'
  version: string
}

export async function checkApiHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch('/api/v1/health', {
    method: 'GET',
    headers: { Accept: 'application/json' },
    signal,
    cache: 'no-store',
  })

  if (!response.ok) {
    throw new Error(`Maestro API returned ${response.status}`)
  }

  return response.json() as Promise<HealthResponse>
}
