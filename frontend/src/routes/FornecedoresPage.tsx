import { useMemo, useState } from 'react';
import { createRoute, Link, useNavigate } from '@tanstack/react-router';
import {
  ArrowLeft,
  BadgeCheck,
  ChevronLeft,
  ChevronRight,
  Clock3,
  PackageCheck,
  ReceiptText,
  Truck,
  WalletCards,
} from 'lucide-react';
import { rootRoute } from './Root';
import { DataTable, type DataTableHeader } from '../components/DataTable';
import { KpiCard } from '../components/KpiCard';
import { TruckLoading } from '../components/TruckLoading';
import {
  useFornecedorProfile,
  useFornecedores,
  type Fornecedor,
  type FornecedorOrder,
  type FornecedorProduct,
} from '../hooks/useFornecedores';

const HISTORY_PAGE_SIZE = 10;

export const fornecedoresRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/fornecedores',
  component: FornecedoresPage,
});

export const fornecedorProfileRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/fornecedores/$id',
  component: FornecedorProfilePage,
});

const fmt = {
  number: (value: number, digits = 2) =>
    value.toLocaleString('pt-BR', {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    }),
  currency: (value: number) =>
    value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }),
  date: (value: string) =>
    new Date(`${value}T00:00:00`).toLocaleDateString('pt-BR'),
};

function formatEmpty(value?: string | null) {
  return value?.trim() ? value : '-';
}

function formatDeliveryTime(days?: number | null) {
  if (days === null || days === undefined) return '-';
  return `${fmt.number(days, 0)} ${days === 1 ? 'dia' : 'dias'}`;
}

function FornecedoresPage() {
  const { data, isFetching, isError } = useFornecedores();
  const fornecedores = data?.items ?? [];
  const kpis = data?.kpis;
  const showLoading = isFetching && fornecedores.length === 0;

  return (
    <div className="flex h-screen flex-col bg-surface">
      <PageHeader
        title="Fornecedores"
        subtitle={
          isFetching
            ? 'Carregando...'
            : `${fornecedores.length} fornecedores cadastrados`
        }
      />

      <main className="flex-1 overflow-auto p-6">
        {!showLoading && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
              <KpiCard
                icon={Truck}
                label="Fornecedores"
                value={fmt.number(kpis?.supplier_count ?? 0, 0)}
                detail="Total cadastrado"
                tone="orange"
              />
              <KpiCard
                icon={Clock3}
                label="Prazo médio de frete"
                value={`${fmt.number(kpis?.avg_delivery_time ?? 0, 2)} dias`}
                detail="Média dos fornecedores"
                tone="blue"
              />
              <KpiCard
                icon={PackageCheck}
                label="Itens por fornecedor"
                value={fmt.number(kpis?.avg_items_per_supplier ?? 0, 2)}
                detail="Média de insumos fornecidos"
                tone="green"
              />
              <KpiCard
                icon={WalletCards}
                label="Melhor custo e prazo"
                value={kpis?.best_value_supplier_name ?? '-'}
                detail={kpis?.best_value_detail ?? 'Sem dados suficientes'}
                tone="cream"
                truncateValue
              />
            </div>

            <DataPanel
              title="Lista de fornecedores"
              subtitle="Clique em um fornecedor para ver produtos e histórico de pedidos."
            >
              <DataTable
                headers={supplierHeaders}
                colSpan={7}
                minWidth="980px"
                isEmpty={isError || fornecedores.length === 0}
                emptyMessage={
                  isError
                    ? 'Nao foi possivel carregar os fornecedores.'
                    : 'Nenhum fornecedor encontrado.'
                }
              >
                {fornecedores.map((fornecedor) => (
                  <FornecedorRow key={fornecedor.id} fornecedor={fornecedor} />
                ))}
              </DataTable>
            </DataPanel>
          </div>
        )}
      </main>
    </div>
  );
}

function FornecedorProfilePage() {
  const navigate = useNavigate();
  const { id } = fornecedorProfileRoute.useParams();
  const { data, isFetching, isError } = useFornecedorProfile(id);
  const showLoading = isFetching && !data;
  const [ordersPage, setOrdersPage] = useState(1);
  const orderTotalPages = Math.max(
    1,
    Math.ceil((data?.orders.length ?? 0) / HISTORY_PAGE_SIZE),
  );
  const currentOrdersPage = Math.min(ordersPage, orderTotalPages);
  const visibleOrders = useMemo(() => {
    const orders = data?.orders ?? [];
    const start = (currentOrdersPage - 1) * HISTORY_PAGE_SIZE;
    return orders.slice(start, start + HISTORY_PAGE_SIZE);
  }, [currentOrdersPage, data?.orders]);

  return (
    <div className="flex h-screen flex-col bg-surface">
      <TruckLoading show={showLoading} />
      <header className="flex flex-shrink-0 items-center gap-3 border-b border-stone-200 bg-white px-8 py-4">
        <button
          type="button"
          onClick={() => navigate({ to: '/fornecedores' })}
          className="flex size-9 items-center justify-center rounded-lg border border-stone-200 text-stone-500 transition hover:bg-stone-50 hover:text-stone-900"
          aria-label="Voltar"
        >
          <ArrowLeft className="size-4" strokeWidth={2} />
        </button>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-bold uppercase tracking-wide text-brand-600">
            Perfil do fornecedor
          </p>
          <h1 className="truncate text-xl font-semibold text-stone-900">
            {data?.supplier.name ?? 'Fornecedor'}
          </h1>
        </div>
      </header>

      <main className="flex-1 overflow-auto p-6">
        {showLoading ? null : isError || !data ? (
          <section className="rounded-xl border border-stone-200 bg-white p-10 text-center text-sm text-stone-400 shadow-sm">
            Fornecedor nao encontrado.
          </section>
        ) : (
          <div className="space-y-6">
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              <KpiCard
                icon={Clock3}
                label="Lead time médio"
                value={`${fmt.number(data.kpis.avg_lead_time, 2)} dias`}
                detail="Data prevista menos data do pedido"
                tone="blue"
              />
              <KpiCard
                icon={ReceiptText}
                label="Pedidos realizados"
                value={fmt.number(data.kpis.orders_count, 0)}
                detail="Histórico registrado"
                tone="orange"
              />
              <KpiCard
                icon={BadgeCheck}
                label="Taxa de entrega"
                value={`${fmt.number(data.kpis.delivery_rate, 2)}%`}
                detail="Pedidos com status entregue"
                tone="green"
              />
            </div>

            <DataPanel
              title="Produtos fornecidos"
              subtitle={`${data.products.length} insumos cadastrados para este fornecedor`}
            >
              <ProductCarousel products={data.products} />
            </DataPanel>

            <DataPanel
              title="Histórico de pedidos"
              subtitle={`${data.orders.length} pedidos registrados`}
            >
              <OrdersTable
                orders={visibleOrders}
                page={currentOrdersPage}
                total={data.orders.length}
                totalPages={orderTotalPages}
                onPageChange={setOrdersPage}
              />
            </DataPanel>
          </div>
        )}
      </main>
    </div>
  );
}

function PageHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <header className="flex flex-shrink-0 items-center justify-between border-b border-stone-200 bg-white px-8 py-5">
      <div>
        <h1 className="text-xl font-semibold text-stone-900">{title}</h1>
        <p className="mt-1 text-xs tabular-nums text-stone-400">{subtitle}</p>
      </div>
      <div className="hidden size-10 items-center justify-center rounded-xl bg-brand-50 text-brand-600 sm:flex">
        <Truck className="size-5" strokeWidth={2} />
      </div>
    </header>
  );
}

function DataPanel({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <section className="overflow-hidden rounded-xl border border-stone-200 bg-white shadow-sm">
      <div className="border-b border-stone-100 px-5 py-4">
        <h2 className="text-sm font-black text-stone-900">{title}</h2>
        <p className="mt-1 text-xs text-stone-400">{subtitle}</p>
      </div>
      {children}
    </section>
  );
}

function BodyCell({
  children,
  align = 'left',
  strong = false,
}: {
  children: React.ReactNode;
  align?: 'left' | 'right';
  strong?: boolean;
}) {
  return (
    <td
      className={[
        'px-5 py-4 text-stone-600',
        align === 'right' ? 'text-right' : 'text-left',
        strong ? 'font-medium text-stone-900' : '',
      ].join(' ')}
    >
      {children}
    </td>
  );
}

const supplierHeaders: DataTableHeader[] = [
  { key: 'supplier', content: 'Fornecedor' },
  { key: 'cnpj', content: 'CNPJ' },
  { key: 'email', content: 'Email' },
  { key: 'phone', content: 'Telefone' },
  { key: 'items', content: 'Itens', align: 'right' },
  { key: 'avg-price', content: 'Preço médio', align: 'right' },
  { key: 'avg-delivery', content: 'Prazo médio', align: 'right' },
];

function FornecedorRow({ fornecedor }: { fornecedor: Fornecedor }) {
  return (
    <tr className="border-b border-stone-100 transition-colors last:border-0 hover:bg-stone-50">
      <BodyCell strong>
        <Link
          to="/fornecedores/$id"
          params={{ id: fornecedor.id }}
          className="text-stone-900 transition hover:text-brand-600 hover:underline"
        >
          {fornecedor.name}
        </Link>
      </BodyCell>
      <BodyCell>{formatEmpty(fornecedor.cnpj)}</BodyCell>
      <BodyCell>{formatEmpty(fornecedor.email)}</BodyCell>
      <BodyCell>{formatEmpty(fornecedor.phone)}</BodyCell>
      <BodyCell align="right">
        {fmt.number(fornecedor.item_count ?? 0, 0)}
      </BodyCell>
      <BodyCell align="right">
        {fornecedor.avg_price === null || fornecedor.avg_price === undefined
          ? '-'
          : fmt.currency(fornecedor.avg_price)}
      </BodyCell>
      <BodyCell align="right">
        <span className="font-medium tabular-nums text-stone-900">
          {formatDeliveryTime(fornecedor.avg_delivery_time)}
        </span>
      </BodyCell>
    </tr>
  );
}

function ProductCarousel({ products }: { products: FornecedorProduct[] }) {
  const [index, setIndex] = useState(0);
  const visibleProducts = products.slice(index, index + 3);
  const canGoBack = index > 0;
  const canGoForward = index + 3 < products.length;

  function move(delta: number) {
    setIndex((current) =>
      Math.max(0, Math.min(Math.max(0, products.length - 1), current + delta)),
    );
  }

  if (products.length === 0) {
    return (
      <div className="px-5 py-16 text-center text-sm text-stone-400">
        Nenhum produto fornecido.
      </div>
    );
  }

  return (
    <div className="p-5">
      <div className="mb-4 flex items-center justify-between gap-3">
        <p className="text-xs text-stone-400">
          Mostrando {index + 1}-{Math.min(index + 3, products.length)} de{' '}
          {products.length}
        </p>
        <div className="flex items-center gap-2">
          <SliderButton disabled={!canGoBack} onClick={() => move(-1)}>
            <ChevronLeft className="size-4" strokeWidth={2} />
          </SliderButton>
          <SliderButton disabled={!canGoForward} onClick={() => move(1)}>
            <ChevronRight className="size-4" strokeWidth={2} />
          </SliderButton>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {visibleProducts.map((product) => (
          <ProductCard key={product.ingredient_id} product={product} />
        ))}
      </div>
    </div>
  );
}

function ProductCard({ product }: { product: FornecedorProduct }) {
  return (
    <article className="overflow-hidden rounded-xl border border-stone-200 bg-white shadow-sm">
      <img
        src={productImage(product)}
        alt={product.name}
        className="h-36 w-full object-cover"
      />
      <div className="space-y-4 p-4">
        <div>
          <h3 className="line-clamp-2 text-sm font-black text-stone-900">
            {product.name}
          </h3>
          <p className="mt-1 text-xs font-medium text-stone-400">
            {product.category}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-3 text-xs">
          <ProductMetric
            label="Estoque atual"
            value={`${fmt.number(product.current_qty, 2)} ${product.unit}`}
          />
          <ProductMetric
            label="Preço unitário"
            value={fmt.currency(product.unit_price)}
          />
        </div>
      </div>
    </article>
  );
}

function ProductMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-stone-50 p-3">
      <p className="text-[11px] font-bold uppercase tracking-wide text-stone-400">
        {label}
      </p>
      <p
        className="mt-1 truncate font-black tabular-nums text-stone-900"
        title={value}
      >
        {value}
      </p>
    </div>
  );
}

function SliderButton({
  children,
  disabled,
  onClick,
}: {
  children: React.ReactNode;
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className="flex size-9 items-center justify-center rounded-lg border border-stone-200 text-stone-500 transition hover:bg-stone-50 disabled:cursor-not-allowed disabled:opacity-30"
    >
      {children}
    </button>
  );
}

function productImage(product: FornecedorProduct) {
  const category = product.category.slice(0, 24);
  const name = product.name.slice(0, 34);
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360">
      <rect width="640" height="360" fill="#232323"/>
      <circle cx="520" cy="80" r="84" fill="#F07820" opacity="0.86"/>
      <circle cx="96" cy="292" r="110" fill="#52B9EB" opacity="0.76"/>
      <path d="M112 124h312c35 0 64 29 64 64v28c0 35-29 64-64 64H112c-35 0-64-29-64-64v-28c0-35 29-64 64-64z" fill="#FFF7D7"/>
      <path d="M155 142h92v78h-92zM274 142h92v78h-92z" fill="#F07820" opacity="0.92"/>
      <text x="64" y="56" font-family="Inter, Arial, sans-serif" font-size="22" fill="#FFF7D7" font-weight="700">${escapeSvg(category)}</text>
      <text x="64" y="318" font-family="Inter, Arial, sans-serif" font-size="30" fill="#FFFFFF" font-weight="900">${escapeSvg(name)}</text>
    </svg>`;

  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

function escapeSvg(value: string) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function OrdersTable({
  orders,
  page,
  total,
  totalPages,
  onPageChange,
}: {
  orders: FornecedorOrder[];
  page: number;
  total: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}) {
  return (
    <DataTable
      headers={orderHeaders}
      colSpan={5}
      minWidth="720px"
      isEmpty={orders.length === 0}
      emptyMessage="Nenhum pedido registrado."
      pagination={{
        page,
        pageSize: HISTORY_PAGE_SIZE,
        total,
        totalPages,
        onPageChange,
      }}
    >
      {orders.map((order) => (
        <tr
          key={order.id}
          className="border-b border-stone-100 transition-colors last:border-0 hover:bg-stone-50"
        >
          <BodyCell strong>{order.id}</BodyCell>
          <BodyCell>{fmt.date(order.order_date)}</BodyCell>
          <BodyCell align="right">{fmt.number(order.items_qty, 2)}</BodyCell>
          <BodyCell align="right">{fmt.currency(order.total_value)}</BodyCell>
          <BodyCell>
            <StatusPill status={order.status} />
          </BodyCell>
        </tr>
      ))}
    </DataTable>
  );
}

const orderHeaders: DataTableHeader[] = [
  { key: 'id', content: 'Pedido' },
  { key: 'date', content: 'Data' },
  { key: 'qty', content: 'Qtd itens', align: 'right' },
  { key: 'value', content: 'Valor total', align: 'right' },
  { key: 'status', content: 'Status' },
];

function StatusPill({ status }: { status: string }) {
  const delivered = status.toLowerCase() === 'entregue';
  return (
    <span
      className={[
        'inline-flex rounded-full px-2.5 py-1 text-xs font-bold capitalize',
        delivered
          ? 'bg-emerald-50 text-emerald-700'
          : 'bg-amber-50 text-amber-700',
      ].join(' ')}
    >
      {status}
    </span>
  );
}
