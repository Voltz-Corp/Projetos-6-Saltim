import { useEffect, useState, type ReactNode } from 'react'
import { createRoute } from '@tanstack/react-router'
import {
  Banknote,
  Check,
  CircleDollarSign,
  CreditCard,
  Eye,
  FileText,
  Package,
  Plus,
  ReceiptText,
  Search,
  Table2,
  Trash2,
  User,
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
}

function VendasPage() {
  const [view, setView] = useState<VendasView>('mesas')
  const [status, setStatus] = useState('')
  const [q, setQ] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
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
  const { data: mesasData } = useVendaMesas()

  const items = vendas?.items ?? []
  const totalRevenue = items
    .filter(item => item.status === 'paga')
    .reduce((total, item) => total + item.total, 0)
  const occupiedTables = mesasData?.mesas.filter(mesa => mesa.status === 'ocupada').length ?? 0

  return (
    <div className="flex h-screen flex-col bg-surface">
      <header className="flex h-[73px] flex-shrink-0 items-center justify-between border-b border-stone-200 bg-white px-8">
        <div>
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
            Historico
          </SwitchButton>
        </div>
      </header>

      <main className="min-h-0 flex-1 overflow-auto p-6">
        <div className="grid gap-4 md:grid-cols-3">
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
            detail="Periodo filtrado"
            tone="blue"
          />
          <KpiCard
            icon={CircleDollarSign}
            label="Receita paga"
            value={fmt.currency(totalRevenue)}
            detail="Somente pagina atual"
            tone="green"
          />
        </div>

        {view === 'mesas' ? (
          <MesasPanel />
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

function MesasPanel() {
  const { data: mesasData, isFetching, isError } = useVendaMesas()
  const createMesaPedido = useCreateMesaPedido()
  const [selectedMesa, setSelectedMesa] = useState<MesaVenda>()
  const [draftComandaId, setDraftComandaId] = useState<string>()

  const mesas = mesasData?.mesas ?? []
  const comandaId = selectedMesa?.comanda_id ?? draftComandaId
  const { data: selectedSale } = useVendaDetail(selectedMesa?.comanda_id ?? undefined)

  async function selectMesa(mesa: MesaVenda) {
    setSelectedMesa(mesa)
    if (mesa.comanda_id) {
      setDraftComandaId(mesa.comanda_id)
      return
    }
    const pedido = await createMesaPedido.mutateAsync(mesa.numero)
    setDraftComandaId(pedido.comanda_id)
  }

  return (
    <section className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
      <div className="min-w-0 rounded-lg border border-stone-200 bg-white p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-black text-stone-900">Mesas</h2>
            <p className="mt-1 text-xs text-stone-400">
              {isFetching ? 'Carregando mesas...' : `${mesas.length} mesas no salao`}
            </p>
          </div>
          {isError && <StatusPill status="erro" />}
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-5">
          {mesas.map(mesa => (
            <button
              key={mesa.numero}
              type="button"
              onClick={() => void selectMesa(mesa)}
              className={[
                'min-h-[112px] rounded-lg border p-4 text-left transition',
                mesa.status === 'ocupada'
                  ? 'border-brand-200 bg-brand-50 text-brand-900 hover:border-brand-400'
                  : 'border-stone-200 bg-stone-50 text-stone-700 hover:border-stone-300 hover:bg-white',
                selectedMesa?.numero === mesa.numero ? 'ring-4 ring-brand-100' : '',
              ].join(' ')}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-black uppercase text-stone-400">Mesa</span>
                <StatusPill status={mesa.status === 'ocupada' ? 'aberta' : 'livre'} />
              </div>
              <p className="mt-2 text-2xl font-black tabular-nums">{mesa.numero}</p>
              <p className="mt-2 text-xs font-bold text-stone-500">
                {mesa.status === 'ocupada'
                  ? `${fmt.number(mesa.items_qty, 0)} itens | ${fmt.currency(mesa.total)}`
                  : 'Livre'}
              </p>
            </button>
          ))}
        </div>
      </div>

      <MesaDetailPanel
        mesa={selectedMesa}
        comandaId={comandaId}
        sale={selectedSale}
        onSaleSaved={sale => {
          setDraftComandaId(sale.comanda_id ?? sale.id)
        }}
      />
    </section>
  )
}

function MesaDetailPanel({
  mesa,
  comandaId,
  sale,
  onSaleSaved,
}: {
  mesa?: MesaVenda
  comandaId?: string
  sale?: VendaDetail
  onSaleSaved: (sale: VendaDetail) => void
}) {
  const [productId, setProductId] = useState('')
  const [qty, setQty] = useState('1')
  const [cart, setCart] = useState<CartItem[]>([])
  const [customerName, setCustomerName] = useState('')
  const [cpfCliente, setCpfCliente] = useState('')
  const [paymentMethod, setPaymentMethod] = useState('pix')
  const [paidAmount, setPaidAmount] = useState('')
  const [message, setMessage] = useState('')

  const { data: products = [], isFetching } = useVendaProdutos()
  const updateItens = useUpdateVendaItens()
  const fecharVenda = useFecharVenda()

  useEffect(() => {
    if (!sale) {
      setCart([])
      setCustomerName('')
      setCpfCliente('')
      setPaidAmount('')
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
    setPaidAmount(sale.status === 'paga' ? String(sale.total) : '')
    setMessage('')
  }, [products, sale])

  const productOptions = products.map(product => ({
    value: product.id,
    label: `${product.name} - ${fmt.currency(product.sale_price)}`,
  }))
  const selectedProduct = products.find(product => product.id === productId)
  const subtotal = cart.reduce((total, item) => total + item.qty * item.product.sale_price, 0)
  const effectivePaid = Number(paidAmount || subtotal)
  const changeAmount = Math.max(effectivePaid - subtotal, 0)
  const canSave = Boolean(mesa && comandaId && cart.length > 0 && subtotal > 0 && sale?.status !== 'paga')
  const canClose = canSave && effectivePaid >= subtotal

  function addItem() {
    setMessage('')
    if (!selectedProduct) {
      setMessage('Selecione um produto.')
      return
    }
    const parsedQty = Number(qty)
    if (!Number.isFinite(parsedQty) || parsedQty <= 0) {
      setMessage('Informe uma quantidade valida.')
      return
    }
    setCart(previous => {
      const existing = previous.find(item => item.product.id === selectedProduct.id)
      if (existing) {
        return previous.map(item =>
          item.product.id === selectedProduct.id
            ? { ...item, qty: item.qty + parsedQty }
            : item,
        )
      }
      return [...previous, { product: selectedProduct, qty: parsedQty }]
    })
    setProductId('')
    setQty('1')
  }

  function removeItem(productIdToRemove: string) {
    setCart(previous => previous.filter(item => item.product.id !== productIdToRemove))
  }

  async function saveItems() {
    if (!mesa || !comandaId) throw new Error('Selecione uma mesa.')
    setMessage('')
    const saved = await updateItens.mutateAsync({
      id: comandaId,
      payload: {
        mesa_numero: mesa.numero,
        customer_name: customerName.trim() || undefined,
        cpf_cliente: onlyDigits(cpfCliente) || undefined,
        items: cart.map(item => ({
          recipe_id: item.product.id,
          quantity: item.qty,
          unit_price: item.product.sale_price,
        })),
      },
    })
    onSaleSaved(saved)
    setMessage('Comanda salva.')
    return saved
  }

  async function closeTable() {
    if (!comandaId || !canClose) return
    setMessage('')
    try {
      await saveItems()
      await fecharVenda.mutateAsync({
        id: comandaId,
        payload: {
          payment_method: paymentMethod,
          paid_amount: effectivePaid,
          cpf_cliente: onlyDigits(cpfCliente) || undefined,
          customer_name: customerName.trim() || undefined,
        },
      })
      setCart([])
      setCustomerName('')
      setCpfCliente('')
      setPaidAmount('')
      setMessage('Mesa fechada e liberada.')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Nao foi possivel fechar a mesa.')
    }
  }

  if (!mesa) {
    return (
      <aside className="rounded-lg border border-stone-200 bg-white p-4">
        <h2 className="text-sm font-black text-stone-900">Comanda</h2>
        <EmptyPanel>Selecione uma mesa.</EmptyPanel>
      </aside>
    )
  }

  return (
    <aside className="rounded-lg border border-stone-200 bg-white p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-black text-stone-900">Mesa {mesa.numero}</h2>
          <p className="mt-1 text-xs font-bold text-stone-400">
            {comandaId ? `Comanda ${comandaId}` : 'Nova comanda'}
          </p>
        </div>
        <StatusPill status={sale?.status ?? 'aberta'} />
      </div>

      <div className="mt-4 grid gap-3">
        <FieldLabel icon={Package} label="Itens" />
        <AppSelect
          value={productId}
          options={productOptions}
          onChange={setProductId}
          placeholder={isFetching ? 'Carregando produtos...' : 'Produto'}
        />
        <div className="grid grid-cols-[1fr_auto] gap-2">
          <input
            value={qty}
            onChange={event => setQty(event.target.value)}
            type="number"
            min="0.01"
            step="0.01"
            className="h-9 rounded-lg border border-stone-200 bg-stone-50 px-3 text-sm font-medium text-stone-900 outline-none transition focus:border-brand-600 focus:ring-4 focus:ring-brand-100"
          />
          <button
            type="button"
            onClick={addItem}
            className="inline-flex h-9 items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 text-sm font-bold text-white transition hover:bg-brand-700"
          >
            <Plus className="size-4" strokeWidth={2} />
            Adicionar
          </button>
        </div>
      </div>

      <div className="mt-4 max-h-[250px] space-y-2 overflow-auto">
        {cart.length === 0 ? (
          <EmptyPanel>Nenhum item na comanda.</EmptyPanel>
        ) : (
          cart.map(item => (
            <div key={item.product.id} className="grid grid-cols-[minmax(0,1fr)_auto] gap-2 rounded-lg border border-stone-200 bg-stone-50 p-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-black text-stone-900">{item.product.name}</p>
                <p className="mt-1 text-xs text-stone-500">
                  {fmt.number(item.qty, 2)} x {fmt.currency(item.product.sale_price)}
                </p>
              </div>
              <button
                type="button"
                onClick={() => removeItem(item.product.id)}
                className="inline-flex size-8 items-center justify-center rounded-lg text-stone-400 transition hover:bg-red-50 hover:text-red-600"
                title="Remover"
              >
                <Trash2 className="size-4" strokeWidth={2} />
              </button>
            </div>
          ))
        )}
      </div>

      <div className="mt-5 grid gap-3">
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
      </div>

      <div className="mt-5 grid gap-3">
        <FieldLabel icon={CreditCard} label="Pagamento" />
        <AppSelect value={paymentMethod} options={PAYMENT_OPTIONS} onChange={setPaymentMethod} />
        <input
          value={paidAmount}
          onChange={event => setPaidAmount(event.target.value)}
          type="number"
          min="0"
          step="0.01"
          placeholder={fmt.currency(subtotal)}
          className="h-9 w-full rounded-lg border border-stone-200 bg-stone-50 px-3 text-sm font-medium text-stone-900 outline-none transition focus:border-brand-600 focus:ring-4 focus:ring-brand-100"
        />
      </div>

      <div className="mt-5 space-y-2 rounded-lg border border-stone-200 bg-stone-50 p-3">
        <SummaryRow label="Subtotal" value={fmt.currency(subtotal)} />
        <SummaryRow label="Pago" value={fmt.currency(effectivePaid || 0)} />
        <SummaryRow label="Troco" value={fmt.currency(changeAmount)} />
        <div className="border-t border-stone-200 pt-2">
          <SummaryRow label="Total" value={fmt.currency(subtotal)} strong />
        </div>
      </div>

      {message && (
        <p className="mt-3 rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-xs font-bold text-stone-600">
          {message}
        </p>
      )}

      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        <button
          type="button"
          disabled={!canSave || updateItens.isPending}
          onClick={() => void saveItems().catch(error => {
            setMessage(error instanceof Error ? error.message : 'Nao foi possivel salvar a comanda.')
          })}
          className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-stone-200 bg-white px-4 text-sm font-black text-stone-700 transition hover:bg-stone-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Check className="size-4" strokeWidth={2.2} />
          Salvar
        </button>
        <button
          type="button"
          disabled={!canClose || fecharVenda.isPending}
          onClick={() => void closeTable()}
          className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 text-sm font-black text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Banknote className="size-4" strokeWidth={2.2} />
          Fechar mesa
        </button>
      </div>
    </aside>
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
  const cancelVenda = useCancelVenda()
  const emptyMessage = isError ? 'Nao foi possivel carregar as vendas.' : 'Nenhuma venda encontrada.'

  return (
    <section className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
      <div className="min-w-0">
        <div className="mb-3 grid gap-3 rounded-lg border border-stone-200 bg-white p-4 lg:grid-cols-[180px_minmax(0,1fr)_150px_150px]">
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
              <BodyCell>{item.mesa_numero ? `Mesa ${item.mesa_numero}` : 'Balcao'}</BodyCell>
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

      <aside className="rounded-lg border border-stone-200 bg-white p-4">
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
              <MiniMetric icon={Banknote} label="Pago" value={fmt.currency(selectedSale.payments.reduce((total, payment) => total + payment.amount, 0))} />
              <MiniMetric icon={User} label="Cliente" value={selectedSale.customer_name ?? selectedSale.customer?.name ?? 'Balcao'} />
              <MiniMetric icon={FileText} label="CPF" value={formatCpf(selectedSale.cpf_cliente ?? selectedSale.customer?.document) ?? '-'} />
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

            {selectedSale.status !== 'cancelada' && (
              <button
                type="button"
                disabled={cancelVenda.isPending}
                onClick={() => cancelVenda.mutate(selectedSale.id)}
                className="inline-flex h-9 w-full items-center justify-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 text-sm font-black text-red-700 transition hover:bg-red-100 disabled:opacity-50"
              >
                <XCircle className="size-4" strokeWidth={2} />
                {cancelVenda.isPending ? 'Cancelando...' : 'Cancelar venda'}
              </button>
            )}
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
    status === 'paga' || status === 'pronto_para_integracao' || status === 'livre'
      ? 'saltim-success-soft'
      : status === 'cancelada' || status === 'cancelado' || status === 'erro'
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
    livre: 'Livre',
    paga: 'Paga',
    cancelada: 'Cancelada',
    pendente_preparacao: 'Pendente fiscal',
    pronto_para_integracao: 'Preparada fiscal',
    cancelado: 'Cancelado',
    erro: 'Erro',
  }
  return labels[status] ?? status
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
