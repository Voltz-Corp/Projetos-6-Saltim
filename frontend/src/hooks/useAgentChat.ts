import { useMutation } from '@tanstack/react-query'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export interface AgentChatRequest {
  message: string
  session_id?: string
}

export interface AgentChatResponse {
  session_id: string
  answer: string
  rows: Array<Record<string, unknown>>
  columns: string[]
  row_count: number
  is_valid: boolean
  error_type?: string | null
}

export function useAgentChat() {
  return useMutation({
    mutationFn: async (payload: AgentChatRequest): Promise<AgentChatResponse> => {
      const response = await fetch(`${API_URL}/api/agent/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!response.ok) {
        throw new Error('Falha ao chamar o agente')
      }

      return response.json()
    },
  })
}
