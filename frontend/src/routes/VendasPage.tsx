import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { createRoute, useNavigate } from '@tanstack/react-router'
import {
  ArrowLeft,
  Banknote,
  CalendarCheck,
  CircleDollarSign,
  CreditCard,
  Eye,
  Package,
  Plus,
  ReceiptText,
  Search,
  Table2,
  Trash2,
  User,
  Utensils,
  XCircle,
  type LucideIcon,
} from 'lucide-react'
import { rootRoute } from './Root'
import { AppSelect } from '../components/AppSelect'
import { DataTable, type DataTableHeader } from '../components/DataTable'
import { KpiCard } from '../components/KpiCard'
import {
  useCancelVenda,
  useCreateMesaPedido,
  useFecharDiaVendas,
  useFecharVenda,
  useUpdateVendaItens,
  useVendaDetail,
  useVendaMesas,
  useVendaProdutos,
  useVendas,
  type MesaVenda,
  type VendaDetail,
  type VendaListItem,
  type VendaProduto,
} from '../hooks/useVendas'

export const vendasRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/vendas',
  component: VendasPage,
})

export const vendaMesaRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/vendas/mesas/$mesaNumero',
  component: VendaMesaPage,
})

type VendasView = 'mesas' | 'history'

interface CartItem {
  product: VendaProduto
  qty: number
}

const PAGE_SIZE_OPTIONS = [10, 25, 50]

const STATUS_OPTIONS = [
  { value: '', label: 'Todos os status' },
  { value: 'paga', label: 'Pagas' },
  { value: 'aberta', label: 'Abertas' },
  { value: 'cancelada', label: 'Canceladas' },
]

const PAYMENT_OPTIONS = [
  { value: 'pix', label: 'Pix' },
  { value: 'cartao_credito', label: 'Cartao credito' },
  { value: 'cartao_debito', label: 'Cartao debito' },
  { value: 'dinheiro', label: 'Dinheiro' },
  { value: 'voucher', label: 'Voucher' },
]

const fmt = {
  number: (value: number, digits = 2) =>
    value.toLocaleString('pt-BR', {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    }),
  currency: (value: number) =>
    value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }),
  dateTime: (value: string) => new Date(value).toLocaleString('pt-BR'),
  date: (value: string) => new Date(`${value}T00:00:00`).toLocaleDateString('pt-BR'),
}

function todayInputValue() {
  return new Date().toLocaleDateString('sv-SE')
}

function VendasPage() {
  const navigate = useNavigate()
  const [view, setView] = useState<VendasView>('mesas')
  const [status, setStatus] = useState('')
  const [q, setQ] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [closeDate, setCloseDate] = useState(todayInputValue())
  const [closeMessage, setCloseMessage] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [selectedSaleId, setSelectedSaleId] = useState<string>()

  const { data: vendas, isFetching, isError } = useVendas({
    status: status || undefined,
    q: q || undefined,
    dateFrom: dateFrom || undefined,
    dateTo: dateTo || undefined,
    page,
    pageSize,
  })
  const { data: mesasData, isFetching: mesasFetching, isError: mesasError } = useVendaMesas()
  const fecharDia = useFecharDiaVendas()

  const items = vendas?.items ?? []
  const mesas = mesasData?.mesas ?? []
  const occupiedTables = mesas.filter(mesa => mesa.status === 'ocupada').length

  async function closeSalesDay() {
    setCloseMessage('')
    try {
      const result = await fecharDia.mutateAsync(closeDate || undefined)
      setCloseMessage(`Dia ${fmt.date(result.date)} fechado com ${result.vendas_dia} vendas pagas.`)
    } catch (error) {
      setCloseMessage(error instanceof Error ? error.message : 'Não foi possível fechar o dia.')
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-surface">
      <header className="flex min-h-[73px] flex-shrink-0 items-center justify-between gap-4 border-b border-stone-200 bg-white px-6 py-4">
        <div className="min-w-0">
          <h1 className="text-xl font-semibold text-stone-900">Vendas</h1>
          <p className="mt-1 text-xs tabular-nums text-stone-400">
            {view === 'mesas'
              ? `${occupiedTables} mesas ocupadas`
              : isFetching
                ? 'Carregando...'
                : `${vendas?.total ?? 0} vendas encontradas`}
          </p>
        </div>
        <div className="inline-flex rounded-lg border border-stone-200 bg-stone-50 p-1">
          <SwitchButton active={view === 'mesas'} onClick={() => setView('mesas')}>
            Mesas
          </SwitchButton>
          <SwitchButton active={view === 'history'} onClick={() => setView('history')}>
            Histórico
          </SwitchButton>
        </div>
      </header>

      <main className="flex-1 overflow-auto p-6">
        <div className="grid gap-4 lg:grid-cols-4">
          <KpiCard
            icon={Table2}
            label="Mesas ocupadas"
            value={fmt.number(occupiedTables, 0)}
            detail={`${mesasData?.total_mesas ?? 20} mesas configuradas`}
            tone="orange"
          />
          <KpiCard
            icon={ReceiptText}
            label="Vendas listadas"
            value={fmt.number(vendas?.total ?? 0, 0)}
            detail="Período filtrado"
            tone="blue"
          />
          <KpiCard
            icon={CircleDollarSign}
            label="Receita paga"
            value={fmt.currency(vendas?.paid_revenue_total ?? 0)}
            detail="Total do filtro"
            tone="green"
          />
          <section className="rounded-xl border border-stone-200 bg-white p-4">
            <div className="flex items-start gap-3">
              <div className="flex size-9 flex-shrink-0 items-center justify-center rounded-xl saltim-info-soft">
                <CalendarCheck className="size-5" strokeWidth={1.9} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-[11px] font-bold uppercase tracking-wide text-stone-500">
                  Fechamento
                </div>
                <div className="mt-2 flex gap-2">
                  <input
                    value={closeDate}
                    onChange={event => setCloseDate(event.target.value)}
                    type="date"
                    className="h-9 min-w-0 flex-1 rounded-lg border border-stone-200 bg-stone-50 px-3 text-sm font-medium text-stone-900 outline-none transition focus:border-brand-600 focus:ring-4 focus:ring-brand-100"
                  />
                  <button
                    type="button"
                    onClick={() => void closeSalesDay()}
                    disabled={fecharDia.isPending}
                    className="inline-flex h-9 items-center justify-center rounded-lg bg-stone-900 px-3 text-xs font-black text-white transition hover:bg-stone-700 disabled:opacity-50"
                  >
                    Fechar
                  </button>
                </div>
                {closeMessage && (
                  <p className="mt-2 truncate text-xs font-bold text-stone-500" title={closeMessage}>
                    {closeMessage}
                  </p>
                )}
              </div>
            </div>
          </section>
        </div>

        {view === 'mesas' ? (
          <MesasGrid
            mesas={mesas}
            isFetching={mesasFetching}
            isError={mesasError}
            onSelectMesa={mesa =>
              navigate({
                to: '/vendas/mesas/$mesaNumero',
                params: { mesaNumero: String(mesa.numero) },
              })
            }
          />
        ) : (
          <HistoryPanel
            status={status}
            setStatus={value => {
              setStatus(value)
              setPage(1)
            }}
            q={q}
            setQ={value => {
              setQ(value)
              setPage(1)
            }}
            dateFrom={dateFrom}
            setDateFrom={value => {
              setDateFrom(value)
              setPage(1)
            }}
            dateTo={dateTo}
            setDateTo={value => {
              setDateTo(value)
              setPage(1)
            }}
            items={items}
            isFetching={isFetching}
            isError={isError}
            page={vendas?.page ?? page}
            pageSize={vendas?.page_size ?? pageSize}
            total={vendas?.total ?? 0}
            totalPages={vendas?.total_pages ?? 1}
            setPage={setPage}
            setPageSize={setPageSize}
            selectedSaleId={selectedSaleId}
            setSelectedSaleId={setSelectedSaleId}
          />
        )}
      </main>
    </div>
  )
}

function MesasGrid({
  mesas,
  isFetching,
  isError,
  onSelectMesa,
}: {
  mesas: MesaVenda[]
  isFetching: boolean
  isError: boolean
  onSelectMesa: (mesa: MesaVenda) => void
}) {
  return (
    <section className="mt-4 rounded-xl border border-stone-200 bg-white p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-black text-stone-900">Mesas</h2>
          <p className="mt-1 text-xs text-stone-400">
            {isFetching ? 'Carregando mesas...' : `${mesas.length} mesas no salão`}
          </p>
        </div>
        {isError && <StatusPill status="erro" />}
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6">
        {mesas.map(mesa => {
          const occupied = mesa.status === 'ocupada'
          return (
            <button
              key={mesa.numero}
              type="button"
              onClick={() => onSelectMesa(mesa)}
              className={[
                'min-h-[132px] rounded-lg border p-4 text-left transition focus:outline-none focus:ring-4',
                occupied
                  ? 'border-red-200 bg-red-50 text-red-950 hover:border-red-300 focus:ring-red-100'
                  : 'border-green-200 bg-green-50 text-green-950 hover:border-green-300 focus:ring-green-100',
              ].join(' ')}
            >
              <div className="flex items-center justify-between gap-2">
                <span
                  className={[
                    'inline-flex size-9 items-center justify-center rounded-lg border',
                    occupied
                      ? 'border-red-200 bg-white text-red-600'
                      : 'border-green-200 bg-white text-green-700',
                  ].join(' ')}
                >
                  <Utensils className="size-5" strokeWidth={2} />
                </span>
                <StatusPill status={occupied ? 'ocupada' : 'livre'} />
              </div>
              <p className="mt-3 text-2xl font-black tabular-nums">Mesa {mesa.numero}</p>
              <p className="mt-2 text-xs font-bold">
                {occupied
                  ? `${fmt.number(mesa.items_qty, 0)} itens | ${fmt.currency(mesa.total)}`
                  : 'Livre'}
              </p>
            </button>
          )
        })}
      </div>
    </section>
  )
}

function VendaMesaPage() {
  const navigate = useNavigate()
  const params = vendaMesaRoute.useParams()
  const mesaNumero = Number(params.mesaNumero)
  const { data: mesasData } = useVendaMesas()
  const mesa = mesasData?.mesas.find(item => item.numero === mesaNumero)
  const [activeComandaId, setActiveComandaId] = useState<string>()

  useEffect(() => {
    setActiveComandaId(mesa?.comanda_id ?? undefined)
  }, [mesa?.comanda_id, mesaNumero])

  const comandaId = mesa?.comanda_id ?? activeComandaId
  const { data: sale } = useVendaDetail(comandaId)

  return (
    <div className="flex min-h-screen flex-col bg-surface">
      <header className="flex min-h-[73px] flex-shrink-0 items-center justify-between gap-4 border-b border-stone-200 bg-white px-6 py-4">
        <div className="flex min-w-0 items-center gap-3">
          <button
            type="button"
            onClick={() => navigate({ to: '/vendas' })}
            className="inline-flex size-10 items-center justify-center rounded-lg border border-stone-200 bg-white text-stone-600 transition hover:bg-stone-50 hover:text-stone-900"
            title="Voltar"
          >
            <ArrowLeft className="size-5" strokeWidth={2} />
          </button>
          <div className="min-w-0">
            <h1 className="text-xl font-semibold text-stone-900">Mesa {mesaNumero}</h1>
            <p className="mt-1 text-xs tabular-nums text-stone-400">
              {comandaId ? `Comanda ${comandaId}` : 'Mesa livre'}
            </p>
          </div>
        </div>
        <StatusPill status={mesa?.status ?? 'livre'} />
      </header>

      <main className="flex-1 overflow-auto p-6">
        <MesaAccount
          mesaNumero={mesaNumero}
          mesa={mesa}
          comandaId={comandaId}
          sale={sale}
          onComandaChange={setActiveComandaId}
          onDone={() => navigate({ to: '/vendas' })}
        />
      </main>
    </div>
  )
}

function MesaAccount({
  mesaNumero,
  mesa,
  comandaId,
  sale,
  onComandaChange,
  onDone,
}: {
  mesaNumero: number
  mesa?: MesaVenda
  comandaId?: string
  sale?: VendaDetail
  onComandaChange: (id?: string) => void
  onDone: () => void
}) {
  const [productId, setProductId] = useState('')
  const [qty, setQty] = useState('1')
  const [cart, setCart] = useState<CartItem[]>([])
  const [customerName, setCustomerName] = useState('')
  const [cpfCliente, setCpfCliente] = useState('')
  const [paymentMethod, setPaymentMethod] = useState('pix')
  const [notes, setNotes] = useState('')
  const [isClosing, setIsClosing] = useState(false)
  const [message, setMessage] = useState('')

  const { data: products = [], isFetching } = useVendaProdutos()
  const createMesaPedido = useCreateMesaPedido()
  const updateItens = useUpdateVendaItens()
  const fecharVenda = useFecharVenda()
  const cancelVenda = useCancelVenda()

  useEffect(() => {
    if (!sale) {
      setCart([])
      setCustomerName('')
      setCpfCliente('')
      setNotes('')
      setIsClosing(false)
      setMessage('')
      return
    }
    const nextCart = sale.items
      .map(item => {
        const product = products.find(candidate => candidate.id === item.recipe_id)
        if (!product) return null
        return { product, qty: item.quantity }
      })
      .filter((item): item is CartItem => Boolean(item))
    setCart(nextCart)
    setCustomerName(sale.customer_name ?? sale.customer?.name ?? '')
    setCpfCliente(maskCpf(sale.cpf_cliente ?? sale.customer?.document ?? ''))
    setPaymentMethod(sale.payment_method ?? 'pix')
    setNotes(sale.notes ?? '')
    setMessage('')
  }, [products, sale])

  const productOptions = useMemo(
    () =>
      products.map(product => ({
        value: product.id,
        label: `${product.name} - ${fmt.currency(product.sale_price)}`,
      })),
    [products],
  )
  const selectedProduct = products.find(product => product.id === productId)
  const subtotal = cart.reduce((total, item) => total + item.qty * item.product.sale_price, 0)
  const canEdit = sale?.status !== 'paga' && sale?.status !== 'cancelada'
  const hasItems = cart.length > 0 && subtotal > 0

  async function addItem() {
    setMessage('')
    if (!selectedProduct) {
      setMessage('Selecione uma receita.')
      return
    }
    const parsedQty = Number(qty)
    if (!Number.isFinite(parsedQty) || parsedQty <= 0) {
      setMessage('Informe uma quantidade válida.')
      return
    }

    const existing = cart.find(item => item.product.id === selectedProduct.id)
    const nextCart = existing
      ? cart.map(item =>
          item.product.id === selectedProduct.id ? { ...item, qty: item.qty + parsedQty } : item,
        )
      : [...cart, { product: selectedProduct, qty: parsedQty }]

    try {
      await saveItems(nextCart, 'Receita adicionada.')
      setCart(nextCart)
      setProductId('')
      setQty('1')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Não foi possível adicionar a receita.')
    }
  }

  async function removeItem(productIdToRemove: string) {
    setMessage('')
    const nextCart = cart.filter(item => item.product.id !== productIdToRemove)
    try {
      if (nextCart.length === 0) {
        if (comandaId) {
          await cancelVenda.mutateAsync(comandaId)
        }
        onComandaChange(undefined)
        setCart([])
        setMessage('Conta esvaziada.')
        return
      }
      await saveItems(nextCart, 'Receita removida.')
      setCart(nextCart)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Não foi possível remover a receita.')
    }
  }

  async function ensureComanda() {
    if (comandaId) return comandaId
    const pedido = await createMesaPedido.mutateAsync(mesaNumero)
    onComandaChange(pedido.comanda_id)
    return pedido.comanda_id
  }

  async function saveItems(itemsToSave = cart, successMessage = 'Conta atualizada.') {
    const totalToSave = itemsToSave.reduce(
      (total, item) => total + item.qty * item.product.sale_price,
      0,
    )
    if (itemsToSave.length === 0 || totalToSave <= 0) {
      throw new Error('Adicione ao menos uma receita.')
    }
    const targetComandaId = await ensureComanda()
    const saved = await updateItens.mutateAsync({
      id: targetComandaId,
      payload: {
        mesa_numero: mesaNumero,
        customer_name: customerName.trim() || undefined,
        cpf_cliente: onlyDigits(cpfCliente) || undefined,
        notes: notes.trim() || undefined,
        items: itemsToSave.map(item => ({
          recipe_id: item.product.id,
          quantity: item.qty,
          unit_price: item.product.sale_price,
        })),
      },
    })
    onComandaChange(saved.comanda_id ?? saved.id)
    setMessage(successMessage)
    return saved.comanda_id ?? saved.id
  }

  async function closeTable() {
    setMessage('')
    try {
      const targetComandaId = await saveItems(cart, '')
      await fecharVenda.mutateAsync({
        id: targetComandaId,
        payload: {
          payment_method: paymentMethod,
          cpf_cliente: onlyDigits(cpfCliente) || undefined,
          customer_name: customerName.trim() || undefined,
          notes: notes.trim() || undefined,
        },
      })
      setMessage('Mesa fechada e liberada.')
      onDone()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Não foi possível fechar a mesa.')
    }
  }

  async function cancelTable() {
    setMessage('')
    try {
      if (comandaId) {
        await cancelVenda.mutateAsync(comandaId)
      }
      setMessage('Mesa cancelada.')
      onDone()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Não foi possível cancelar a mesa.')
    }
  }

  return (
    <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
      <div className="min-w-0 rounded-xl border border-stone-200 bg-white p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-black text-stone-900">Receitas da conta</h2>
            <p className="mt-1 text-xs text-stone-400">
              {mesa?.status === 'ocupada' ? 'Mesa ocupada' : 'Mesa livre'}
            </p>
          </div>
          <StatusPill status={sale?.status ?? mesa?.status ?? 'livre'} />
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-[minmax(0,1fr)_120px_auto]">
          <AppSelect
            value={productId}
            options={productOptions}
            onChange={setProductId}
            placeholder={isFetching ? 'Carregando receitas...' : 'Receita'}
          />
          <input
            value={qty}
            onChange={event => setQty(event.target.value)}
            type="number"
            min="0.01"
            step="0.01"
            disabled={!canEdit}
            className="h-9 rounded-lg border border-stone-200 bg-stone-50 px-3 text-sm font-medium text-stone-900 outline-none transition focus:border-brand-600 focus:ring-4 focus:ring-brand-100 disabled:opacity-50"
          />
          <button
            type="button"
            disabled={!canEdit || updateItens.isPending || createMesaPedido.isPending}
            onClick={() => void addItem()}
            className="inline-flex h-9 items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 text-sm font-bold text-white transition hover:bg-brand-700 disabled:opacity-50"
          >
            <Plus className="size-4" strokeWidth={2} />
            Adicionar
          </button>
        </div>

        <div className="mt-4 space-y-2">
          {cart.length === 0 ? (
            <EmptyPanel>Nenhuma receita adicionada.</EmptyPanel>
          ) : (
            cart.map(item => (
              <div
                key={item.product.id}
                className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-3 rounded-lg border border-stone-200 bg-stone-50 p-3"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-black text-stone-900">{item.product.name}</p>
                  <p className="mt-1 text-xs text-stone-500">
                    {fmt.number(item.qty, 2)} x {fmt.currency(item.product.sale_price)}
                  </p>
                </div>
                <p className="text-sm font-black tabular-nums text-stone-900">
                  {fmt.currency(item.qty * item.product.sale_price)}
                </p>
                <button
                  type="button"
                  disabled={!canEdit || updateItens.isPending || cancelVenda.isPending}
                  onClick={() => void removeItem(item.product.id)}
                  className="inline-flex size-8 items-center justify-center rounded-lg text-stone-400 transition hover:bg-red-50 hover:text-red-600 disabled:opacity-40"
                  title="Remover"
                >
                  <Trash2 className="size-4" strokeWidth={2} />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      <aside className="rounded-xl border border-stone-200 bg-white p-4">
        <h2 className="text-sm font-black text-stone-900">Ações da mesa</h2>
        <div className="mt-4 space-y-2 rounded-lg border border-stone-200 bg-stone-50 p-3">
          <SummaryRow label="Receitas" value={fmt.number(cart.length, 0)} />
          <SummaryRow label="Total" value={fmt.currency(subtotal)} strong />
        </div>

        <button
          type="button"
          disabled={!canEdit || !hasItems}
          onClick={() => setIsClosing(true)}
          className="mt-4 inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 text-sm font-black text-white transition hover:bg-brand-700 disabled:opacity-50"
        >
          <Banknote className="size-4" strokeWidth={2.2} />
          Fechar mesa
        </button>

        <button
          type="button"
          disabled={cancelVenda.isPending}
          onClick={() => void cancelTable()}
          className="mt-2 inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 text-sm font-black text-red-700 transition hover:bg-red-100 disabled:opacity-50"
        >
          <XCircle className="size-4" strokeWidth={2.2} />
          Cancelar mesa
        </button>

        {isClosing && (
          <div className="mt-4 space-y-3 rounded-lg border border-stone-200 bg-white p-3">
            <FieldLabel icon={User} label="Cliente" />
            <input
              value={customerName}
              onChange={event => setCustomerName(event.target.value)}
              placeholder="Nome opcional"
              className="h-9 w-full rounded-lg border border-stone-200 bg-stone-50 px-3 text-sm font-medium text-stone-900 outline-none transition focus:border-brand-600 focus:ring-4 focus:ring-brand-100"
            />
            <input
              value={cpfCliente}
              onChange={event => setCpfCliente(maskCpf(event.target.value))}
              placeholder="CPF"
              inputMode="numeric"
              className="h-9 w-full rounded-lg border border-stone-200 bg-stone-50 px-3 text-sm font-medium text-stone-900 outline-none transition focus:border-brand-600 focus:ring-4 focus:ring-brand-100"
            />
            <FieldLabel icon={CreditCard} label="Forma de pagamento" />
            <AppSelect value={paymentMethod} options={PAYMENT_OPTIONS} onChange={setPaymentMethod} />
            <textarea
              value={notes}
              onChange={event => setNotes(event.target.value)}
              placeholder="Observações"
              rows={3}
              className="w-full resize-none rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-sm font-medium text-stone-900 outline-none transition focus:border-brand-600 focus:ring-4 focus:ring-brand-100"
            />
            <button
              type="button"
              disabled={fecharVenda.isPending}
              onClick={() => void closeTable()}
              className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-stone-900 px-4 text-sm font-black text-white transition hover:bg-stone-700 disabled:opacity-50"
            >
              <Banknote className="size-4" strokeWidth={2.2} />
              Efetuar pagamento
            </button>
          </div>
        )}

        {message && (
          <p className="mt-3 rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-xs font-bold text-stone-600">
            {message}
          </p>
        )}
      </aside>
    </section>
  )
}

function HistoryPanel({
  status,
  setStatus,
  q,
  setQ,
  dateFrom,
  setDateFrom,
  dateTo,
  setDateTo,
  items,
  isFetching,
  isError,
  page,
  pageSize,
  total,
  totalPages,
  setPage,
  setPageSize,
  selectedSaleId,
  setSelectedSaleId,
}: {
  status: string
  setStatus: (value: string) => void
  q: string
  setQ: (value: string) => void
  dateFrom: string
  setDateFrom: (value: string) => void
  dateTo: string
  setDateTo: (value: string) => void
  items: VendaListItem[]
  isFetching: boolean
  isError: boolean
  page: number
  pageSize: number
  total: number
  totalPages: number
  setPage: (value: number) => void
  setPageSize: (value: number) => void
  selectedSaleId?: string
  setSelectedSaleId: (value?: string) => void
}) {
  const { data: selectedSale } = useVendaDetail(selectedSaleId)
  const emptyMessage = isError ? 'Não foi possível carregar as vendas.' : 'Nenhuma venda encontrada.'

  return (
    <section className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
      <div className="min-w-0">
        <div className="mb-3 grid gap-3 rounded-xl border border-stone-200 bg-white p-4 lg:grid-cols-[180px_minmax(0,1fr)_150px_150px]">
          <AppSelect value={status} options={STATUS_OPTIONS} onChange={setStatus} />
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-stone-400" />
            <input
              value={q}
              onChange={event => setQ(event.target.value)}
              placeholder="Comanda, venda, CPF ou cliente"
              className="h-9 w-full rounded-lg border border-stone-200 bg-stone-50 pl-9 pr-3 text-sm font-medium text-stone-900 outline-none transition focus:border-brand-600 focus:ring-4 focus:ring-brand-100"
            />
          </div>
          <input
            value={dateFrom}
            onChange={event => setDateFrom(event.target.value)}
            type="date"
            className="h-9 rounded-lg border border-stone-200 bg-stone-50 px-3 text-sm font-medium text-stone-900 outline-none transition focus:border-brand-600 focus:ring-4 focus:ring-brand-100"
          />
          <input
            value={dateTo}
            onChange={event => setDateTo(event.target.value)}
            type="date"
            className="h-9 rounded-lg border border-stone-200 bg-stone-50 px-3 text-sm font-medium text-stone-900 outline-none transition focus:border-brand-600 focus:ring-4 focus:ring-brand-100"
          />
        </div>

        <DataTable
          headers={historyHeaders}
          isEmpty={isFetching || items.length === 0}
          isLoading={isFetching}
          emptyMessage={emptyMessage}
          loadingMessage="Carregando vendas..."
          minWidth="980px"
          pagination={{
            page,
            pageSize,
            total,
            totalPages,
            onPageChange: setPage,
            onPageSizeChange: value => {
              setPageSize(value)
              setPage(1)
            },
            pageSizeOptions: PAGE_SIZE_OPTIONS,
          }}
        >
          {items.map(item => (
            <tr key={item.id} className="border-b border-stone-100 last:border-0">
              <BodyCell strong>{item.id}</BodyCell>
              <BodyCell>{fmt.dateTime(item.date_time)}</BodyCell>
              <BodyCell>{item.mesa_numero ? `Mesa ${item.mesa_numero}` : 'Balcão'}</BodyCell>
              <BodyCell>{item.customer_name ?? formatCpf(item.cpf_cliente) ?? '-'}</BodyCell>
              <BodyCell align="right">{fmt.number(item.items_qty, 2)}</BodyCell>
              <BodyCell align="right">{fmt.currency(item.total)}</BodyCell>
              <BodyCell>
                <StatusPill status={item.status} />
              </BodyCell>
              <BodyCell align="center">
                <button
                  type="button"
                  onClick={() => setSelectedSaleId(item.id)}
                  className="inline-flex size-8 items-center justify-center rounded-lg text-stone-500 transition hover:bg-brand-50 hover:text-brand-700"
                  title="Ver detalhes"
                >
                  <Eye className="size-4" strokeWidth={2} />
                </button>
              </BodyCell>
            </tr>
          ))}
        </DataTable>
      </div>

      <aside className="rounded-xl border border-stone-200 bg-white p-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-sm font-black text-stone-900">Detalhe</h2>
          {selectedSale?.status && <StatusPill status={selectedSale.status} />}
        </div>

        {!selectedSale ? (
          <EmptyPanel>Selecione uma venda.</EmptyPanel>
        ) : (
          <div className="mt-4 space-y-4">
            <div>
              <p className="text-xs font-bold uppercase text-stone-400">{selectedSale.id}</p>
              <p className="mt-1 text-sm font-black text-stone-900">
                {fmt.currency(selectedSale.total)}
              </p>
              <p className="mt-1 text-xs text-stone-500">{fmt.dateTime(selectedSale.date_time)}</p>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <MiniMetric icon={Package} label="Itens" value={fmt.number(selectedSale.items.length, 0)} />
              <MiniMetric icon={Banknote} label="Pagamento" value={paymentLabel(selectedSale.payment_method)} />
              <MiniMetric icon={User} label="Cliente" value={selectedSale.customer_name ?? selectedSale.customer?.name ?? 'Balcão'} />
              <MiniMetric icon={ReceiptText} label="CPF" value={formatCpf(selectedSale.cpf_cliente ?? selectedSale.customer?.document) ?? '-'} />
            </div>

            <div className="space-y-2">
              {selectedSale.items.map(item => (
                <div key={item.id} className="rounded-lg border border-stone-200 bg-stone-50 p-3">
                  <p className="truncate text-sm font-black text-stone-900">{item.recipe_name}</p>
                  <p className="mt-1 text-xs text-stone-500">
                    {fmt.number(item.quantity, 2)} x {fmt.currency(item.unit_price)}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </aside>
    </section>
  )
}

function SwitchButton({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        'rounded-md px-3 py-1.5 text-sm font-black transition-colors',
        active ? 'bg-white text-brand-700 shadow-sm' : 'text-stone-500 hover:text-stone-900',
      ].join(' ')}
    >
      {children}
    </button>
  )
}

function BodyCell({
  children,
  align = 'left',
  strong = false,
}: {
  children: ReactNode
  align?: 'left' | 'right' | 'center'
  strong?: boolean
}) {
  return (
    <td
      className={[
        'px-4 py-3 text-sm text-stone-600',
        align === 'right' ? 'text-right' : '',
        align === 'center' ? 'text-center' : '',
        strong ? 'font-black text-stone-900' : '',
      ].join(' ')}
    >
      {children}
    </td>
  )
}

function StatusPill({ status }: { status: string }) {
  const classes =
    status === 'paga' || status === 'livre'
      ? 'saltim-success-soft'
      : status === 'cancelada' || status === 'cancelado' || status === 'erro' || status === 'ocupada'
        ? 'saltim-danger-soft'
        : 'saltim-alert-soft'

  return (
    <span className={`inline-flex rounded-full border px-2.5 py-1 text-[11px] font-black ${classes}`}>
      {statusLabel(status)}
    </span>
  )
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    aberta: 'Aberta',
    ocupada: 'Ocupada',
    livre: 'Livre',
    paga: 'Paga',
    cancelada: 'Cancelada',
    cancelado: 'Cancelado',
    erro: 'Erro',
  }
  return labels[status] ?? status
}

function paymentLabel(value?: string | null) {
  if (!value) return '-'
  return PAYMENT_OPTIONS.find(option => option.value === value)?.label ?? value
}

function FieldLabel({
  icon: Icon,
  label,
}: {
  icon: LucideIcon
  label: string
}) {
  return (
    <div className="flex items-center gap-2 text-xs font-black uppercase text-stone-500">
      <Icon className="size-4" strokeWidth={2} />
      {label}
    </div>
  )
}

function SummaryRow({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-xs font-bold text-stone-500">{label}</span>
      <span className={strong ? 'text-base font-black text-stone-900' : 'text-sm font-black text-stone-700'}>
        {value}
      </span>
    </div>
  )
}

function EmptyPanel({ children }: { children: ReactNode }) {
  return (
    <div className="mt-4 rounded-lg border border-dashed border-stone-200 bg-stone-50 px-4 py-12 text-center text-sm font-bold text-stone-400">
      {children}
    </div>
  )
}

function MiniMetric({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon
  label: string
  value: string
}) {
  return (
    <div className="min-w-0 rounded-lg border border-stone-200 bg-stone-50 p-3">
      <div className="flex items-center gap-2 text-[11px] font-black uppercase text-stone-400">
        <Icon className="size-3.5" strokeWidth={2} />
        {label}
      </div>
      <p className="mt-1 truncate text-xs font-black text-stone-900" title={value}>
        {value}
      </p>
    </div>
  )
}

function onlyDigits(value?: string | null) {
  return (value ?? '').replace(/\D/g, '')
}

function maskCpf(value: string) {
  const digits = onlyDigits(value).slice(0, 11)
  return digits
    .replace(/(\d{3})(\d)/, '$1.$2')
    .replace(/(\d{3})(\d)/, '$1.$2')
    .replace(/(\d{3})(\d{1,2})$/, '$1-$2')
}

function formatCpf(value?: string | null) {
  const digits = onlyDigits(value)
  if (!digits) return null
  if (digits.length !== 11) return value ?? null
  return maskCpf(digits)
}

const historyHeaders: DataTableHeader[] = [
  { key: 'id', content: 'Comanda' },
  { key: 'date', content: 'Data' },
  { key: 'mesa', content: 'Mesa' },
  { key: 'customer', content: 'Cliente/CPF' },
  { key: 'items', content: 'Itens', align: 'right' },
  { key: 'total', content: 'Total', align: 'right' },
  { key: 'status', content: 'Status' },
  { key: 'actions', content: '', align: 'center' },
]
