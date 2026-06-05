import { FormEvent, PointerEvent, useMemo, useRef, useState } from 'react'
import { Bot, MessageCircle, Send, X } from 'lucide-react'
import { useAgentChat, type AgentChatResponse } from '../hooks/useAgentChat'
import { cn } from '../lib/cn'

type ChatMessage = {
  id: string
  role: 'user' | 'agent'
  content: string
  response?: AgentChatResponse
}

type PanelPosition = {
  left: number
  top: number
}

type DragState = {
  startX: number
  startY: number
  startLeft: number
  startTop: number
  width: number
  height: number
} | null

const PANEL_MARGIN = 12

const suggestions = [
  'Quais ingredientes estão com estoque zerado?',
  'Quais receitas geraram mais faturamento nos últimos 90 dias?',
  'Quais pedidos estão em trânsito?',
  'Quais itens precisam de compra?',
]

function createId() {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function formatCell(value: unknown) {
  if (value === null || value === undefined || value === '') return '-'
  if (typeof value === 'number') {
    return Intl.NumberFormat('pt-BR', {
      maximumFractionDigits: 2,
    }).format(value)
  }
  if (typeof value === 'boolean') return value ? 'Sim' : 'Não'
  return String(value)
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max)
}

function AgentRowsPreview({ response }: { response: AgentChatResponse }) {
  if (!response.rows.length || !response.columns.length) return null

  const columns = response.columns.slice(0, 4)

  return (
    <div className="mt-3 overflow-hidden rounded-lg border border-stone-200 bg-white">
      <div className="max-h-44 overflow-auto">
        <table className="min-w-full text-left text-[11px]">
          <thead className="sticky top-0 bg-stone-50 text-stone-500">
            <tr>
              {columns.map(column => (
                <th key={column} className="px-2.5 py-2 font-black">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-100">
            {response.rows.map((row, index) => (
              <tr key={index}>
                {columns.map(column => (
                  <td key={column} className="max-w-[130px] truncate px-2.5 py-2 text-stone-700">
                    {formatCell(row[column])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {response.row_count > response.rows.length && (
        <div className="border-t border-stone-100 px-2.5 py-1.5 text-[11px] font-semibold text-stone-400">
          Mostrando {response.rows.length} de {response.row_count} registros.
        </div>
      )}
    </div>
  )
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user'

  return (
    <div className={cn('flex', isUser ? 'justify-end' : 'justify-start')}>
      <div
        className={cn(
          'max-w-[86%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed',
          isUser
            ? 'bg-brand-600 text-white'
            : 'border border-stone-200 bg-white text-stone-800',
        )}
      >
        <p>{message.content}</p>
        {message.response && !isUser && <AgentRowsPreview response={message.response} />}
      </div>
    </div>
  )
}

export function AgentChatWidget() {
  const [isOpen, setIsOpen] = useState(false)
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [panelPosition, setPanelPosition] = useState<PanelPosition | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const panelRef = useRef<HTMLElement | null>(null)
  const dragState = useRef<DragState>(null)
  const sessionId = useRef(`agent-${createId()}`)
  const chat = useAgentChat()

  const hasMessages = messages.length > 0
  const canSend = input.trim().length > 0 && !chat.isPending

  const introContent = useMemo(
    () => (
      <div className="flex flex-1 flex-col items-center px-5 pt-8 text-center">
        <span className="flex size-12 items-center justify-center rounded-xl bg-brand-600 text-white">
          <Bot className="size-6" strokeWidth={2.1} />
        </span>
        <h2 className="mt-4 text-xl font-black text-stone-900">Como posso ajudar?</h2>
        <p className="mt-1 max-w-[300px] text-sm font-medium text-stone-500">
          Faça perguntas sobre estoque, vendas, fornecedores e pedidos.
        </p>
        <div className="mt-8 w-full space-y-2.5">
          {suggestions.map(suggestion => (
            <button
              key={suggestion}
              type="button"
              onClick={() => submitMessage(suggestion)}
              disabled={chat.isPending}
              className="flex min-h-9 w-full items-center gap-2 rounded-lg bg-blue-100 px-3 text-left text-sm font-medium text-stone-800 transition hover:bg-blue-200 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <span className="flex size-5 flex-shrink-0 items-center justify-center rounded-full border border-stone-700 text-xs font-black">
                ?
              </span>
              <span className="min-w-0 truncate">{suggestion}</span>
            </button>
          ))}
        </div>
      </div>
    ),
    [chat.isPending],
  )

  async function submitMessage(rawMessage?: string) {
    const message = (rawMessage ?? input).trim()
    if (!message || chat.isPending) return

    setInput('')
    setMessages(current => [
      ...current,
      { id: createId(), role: 'user', content: message },
    ])

    try {
      const response = await chat.mutateAsync({
        message,
        session_id: sessionId.current,
      })
      sessionId.current = response.session_id
      setMessages(current => [
        ...current,
        {
          id: createId(),
          role: 'agent',
          content: response.answer,
          response,
        },
      ])
    } catch {
      setMessages(current => [
        ...current,
        {
          id: createId(),
          role: 'agent',
          content: 'Não consegui falar com o agente agora.',
        },
      ])
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    submitMessage()
  }

  function handleDragStart(event: PointerEvent<HTMLElement>) {
    if (event.button !== 0) return
    const panel = panelRef.current
    if (!panel) return

    const rect = panel.getBoundingClientRect()
    dragState.current = {
      startX: event.clientX,
      startY: event.clientY,
      startLeft: rect.left,
      startTop: rect.top,
      width: rect.width,
      height: rect.height,
    }
    setPanelPosition({ left: rect.left, top: rect.top })
    setIsDragging(true)
    event.currentTarget.setPointerCapture(event.pointerId)
  }

  function handleDragMove(event: PointerEvent<HTMLElement>) {
    if (!dragState.current) return

    const nextLeft = dragState.current.startLeft + event.clientX - dragState.current.startX
    const nextTop = dragState.current.startTop + event.clientY - dragState.current.startY
    const maxLeft = window.innerWidth - dragState.current.width - PANEL_MARGIN
    const maxTop = window.innerHeight - dragState.current.height - PANEL_MARGIN

    setPanelPosition({
      left: clamp(nextLeft, PANEL_MARGIN, Math.max(PANEL_MARGIN, maxLeft)),
      top: clamp(nextTop, PANEL_MARGIN, Math.max(PANEL_MARGIN, maxTop)),
    })
  }

  function handleDragEnd(event: PointerEvent<HTMLElement>) {
    if (!dragState.current) return
    dragState.current = null
    setIsDragging(false)
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId)
    }
  }

  return (
    <>
      {isOpen && (
        <section
          ref={panelRef}
          style={panelPosition ? { left: panelPosition.left, top: panelPosition.top } : undefined}
          className={cn(
            'fixed z-[70] flex h-[min(650px,calc(100vh-110px))] w-[420px] max-w-[calc(100vw-24px)] flex-col overflow-hidden rounded-2xl border border-stone-200 bg-[#f8f8f8]',
            panelPosition ? '' : 'bottom-24 right-5 max-sm:right-3',
            isDragging ? 'select-none' : '',
          )}
        >
          <header
            onPointerDown={handleDragStart}
            onPointerMove={handleDragMove}
            onPointerUp={handleDragEnd}
            onPointerCancel={handleDragEnd}
            className={cn(
              'flex min-h-[58px] touch-none items-center justify-between border-b border-stone-300 px-5',
              isDragging ? 'cursor-grabbing' : 'cursor-grab',
            )}
          >
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-stone-900">Agente Saltim</p>
              <p className="truncate text-xs text-stone-500">Pergunte sobre estoque, vendas e pedidos</p>
            </div>
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              className="flex size-9 flex-shrink-0 items-center justify-center rounded-lg text-stone-500 transition hover:bg-stone-100 hover:text-stone-900"
              aria-label="Fechar chat"
              onPointerDown={event => event.stopPropagation()}
            >
              <X className="size-5" strokeWidth={1.8} />
            </button>
          </header>

          <div className="flex min-h-0 flex-1 flex-col">
            {!hasMessages ? (
              introContent
            ) : (
              <div className="flex-1 space-y-3 overflow-auto px-4 py-4">
                {messages.map(message => (
                  <MessageBubble key={message.id} message={message} />
                ))}
                {chat.isPending && (
                  <div className="flex justify-start">
                    <div className="rounded-2xl border border-stone-200 bg-white px-3.5 py-2.5 text-sm font-medium text-stone-400">
                      Pensando...
                    </div>
                  </div>
                )}
              </div>
            )}

            <form onSubmit={handleSubmit} className="border-t border-stone-200 bg-[#f8f8f8] p-4">
              <div className="grid grid-cols-[minmax(0,1fr)_36px_36px] items-center gap-1 rounded-xl border border-stone-300 bg-white px-2 py-1.5">
                <input
                  value={input}
                  onChange={event => setInput(event.target.value)}
                  disabled={chat.isPending}
                  className="h-9 min-w-0 bg-transparent px-2 text-sm text-stone-800 outline-none placeholder:text-stone-400 disabled:cursor-not-allowed"
                  placeholder="Pergunte sobre estoque, vendas, pedidos..."
                />
                <button
                  type="submit"
                  disabled={!canSend}
                  className="flex size-9 items-center justify-center rounded-lg bg-blue-600 text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                  aria-label="Enviar pergunta"
                >
                  <Send className="size-4" strokeWidth={2} />
                </button>
                <button
                  type="button"
                  onClick={() => setInput('')}
                  className="flex size-9 items-center justify-center rounded-lg text-stone-500 transition hover:bg-stone-100 hover:text-stone-900"
                  aria-label="Limpar pergunta"
                >
                  <X className="size-4" strokeWidth={1.8} />
                </button>
              </div>
            </form>
          </div>
        </section>
      )}

      <button
        type="button"
        onClick={() => setIsOpen(value => !value)}
        className="fixed bottom-5 right-5 z-[71] flex size-14 items-center justify-center rounded-full bg-brand-600 text-white transition hover:bg-brand-700 max-sm:right-3"
        aria-label={isOpen ? 'Fechar agente' : 'Abrir agente'}
      >
        {isOpen ? <X className="size-6" strokeWidth={2} /> : <MessageCircle className="size-6" strokeWidth={2} />}
      </button>
    </>
  )
}
