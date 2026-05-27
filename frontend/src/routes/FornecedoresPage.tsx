import { useMemo, useState } from 'react';
import { createRoute, Link, useNavigate } from '@tanstack/react-router';
import {
  ArrowLeft,
  BadgeCheck,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Plus,
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
const SUPPLIER_PAGE_SIZE_OPTIONS = [10, 25, 50];
const ORDER_PAGE_SIZE_OPTIONS = [5, 10, 25, 50];

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
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const totalPages = Math.max(1, Math.ceil(fornecedores.length / pageSize));
  const currentPage = Math.min(page, totalPages);
  const visibleFornecedores = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return fornecedores.slice(start, start + pageSize);
  }, [currentPage, fornecedores, pageSize]);

  return (
    <div className="flex h-screen flex-col bg-surface">
      <TruckLoading show={showLoading} />
      <PageHeader
        title="Fornecedores"
        subtitle={
          isFetching
            ? 'Carregando...'
            : `${fornecedores.length} fornecedores cadastrados`
          }
        action={
          <Link
            to="/fornecedores/novo"
            className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-bold text-white transition hover:bg-brand-700"
          >
            <Plus className="size-4" strokeWidth={2} />
            Adicionar fornecedor
          </Link>
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
                value={formatDeliveryTime(kpis?.avg_delivery_time ?? 0)}
                detail="Média dos fornecedores"
                tone="blue"
              />
              <KpiCard
                icon={PackageCheck}
                label="Insumos por fornecedor"
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
                embedded
                pagination={{
                  page: currentPage,
                  pageSize,
                  total: fornecedores.length,
                  totalPages,
                  pageSizeOptions: SUPPLIER_PAGE_SIZE_OPTIONS,
                  onPageChange: setPage,
                  onPageSizeChange: (value) => {
                    setPageSize(value);
                    setPage(1);
                  },
                }}
              >
                {visibleFornecedores.map((fornecedor) => (
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
  const [ordersPageSize, setOrdersPageSize] = useState(HISTORY_PAGE_SIZE);
  const orderTotalPages = Math.max(
    1,
    Math.ceil((data?.orders.length ?? 0) / ordersPageSize),
  );
  const currentOrdersPage = Math.min(ordersPage, orderTotalPages);
  const visibleOrders = useMemo(() => {
    const orders = data?.orders ?? [];
    const start = (currentOrdersPage - 1) * ordersPageSize;
    return orders.slice(start, start + ordersPageSize);
  }, [currentOrdersPage, data?.orders, ordersPageSize]);

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
                label="Tempo médio de entrega"
                value={formatDeliveryTime(data.kpis.avg_lead_time)}
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
                pageSize={ordersPageSize}
                onPageSizeChange={(value) => {
                  setOrdersPageSize(value);
                  setOrdersPage(1);
                }}
              />
            </DataPanel>
          </div>
        )}
      </main>
    </div>
  );
}

function PageHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle: string;
  action?: React.ReactNode;
}) {
  return (
    <header className="flex flex-shrink-0 items-center justify-between border-b border-stone-200 bg-white px-8 py-5">
      <div>
        <h1 className="text-xl font-semibold text-stone-900">{title}</h1>
        <p className="mt-1 text-xs tabular-nums text-stone-400">{subtitle}</p>
      </div>
      <div className="flex items-center gap-3">
        {action}
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
    <section className="overflow-hidden rounded-xl border border-stone-200 bg-white">
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
  align?: 'left' | 'right' | 'center';
  strong?: boolean;
}) {
  return (
    <td
      className={[
        'px-5 py-4 text-stone-600',
        align === 'right' ? 'text-right' : align === 'center' ? 'text-center' : 'text-left',
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
      <BodyCell>{formatDocument(fornecedor.cnpj)}</BodyCell>
      <BodyCell>{formatEmpty(fornecedor.email)}</BodyCell>
      <BodyCell>{formatPhone(fornecedor.phone)}</BodyCell>
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
  const visibleProducts = products.slice(index, index + 5);
  const canGoBack = index > 0;
  const canGoForward = index + 5 < products.length;

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
          Mostrando {index + 1}-{Math.min(index + 5, products.length)} de{' '}
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

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-5">
        {visibleProducts.map((product) => (
          <ProductCard key={product.ingredient_id} product={product} />
        ))}
      </div>
    </div>
  );
}

function ProductCard({ product }: { product: FornecedorProduct }) {
  return (
    <article className="overflow-hidden rounded-xl border border-stone-200 bg-white">
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
  const variant = categoryVariant(product.category);
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360">
      <rect width="640" height="360" fill="#232323"/>
      ${variant.background}
      ${variant.shape}
      <text x="64" y="56" font-family="Inter, Arial, sans-serif" font-size="22" fill="#FFF7D7" font-weight="700">${escapeSvg(category)}</text>
      <text x="64" y="318" font-family="Inter, Arial, sans-serif" font-size="30" fill="#F7F7F7" font-weight="900">${escapeSvg(name)}</text>
    </svg>`;

  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

function categoryVariant(category: string) {
  const normalized = category
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();

  if (normalized.includes('acucar') || normalized.includes('mel')) {
    return {
      background:
        '<circle cx="526" cy="94" r="86" fill="#F07820" opacity="0.88"/><circle cx="96" cy="292" r="108" fill="#EDE0B4" opacity="0.55"/>',
      shape:
        '<path d="M182 246l72-116h116l72 116z" fill="#FFF7D7"/><path d="M240 148h148v116H240z" fill="#F07820" opacity="0.9"/><path d="M206 246h210" stroke="#FFF7D7" stroke-width="24" stroke-linecap="round"/>',
    };
  }
  if (normalized.includes('bebida')) {
    return {
      background:
        '<circle cx="520" cy="80" r="84" fill="#F07820" opacity="0.9"/><circle cx="96" cy="292" r="110" fill="#52B9EB" opacity="0.76"/>',
      shape:
        '<rect x="242" y="92" width="150" height="198" rx="34" fill="#FFF7D7"/><path d="M258 134h118v98H258z" fill="#52B9EB" opacity="0.88"/><path d="M280 92h74v-24h-74z" fill="#F07820"/><circle cx="318" cy="246" r="20" fill="#F07820"/>',
    };
  }
  if (normalized.includes('chocolate') || normalized.includes('cacau')) {
    return {
      background:
        '<circle cx="526" cy="92" r="86" fill="#F23B3B" opacity="0.82"/><circle cx="94" cy="292" r="108" fill="#F07820" opacity="0.7"/>',
      shape:
        '<rect x="176" y="112" width="288" height="166" rx="28" fill="#FFF7D7"/><path d="M202 142h236M202 190h236M250 122v142M342 122v142" stroke="#232323" stroke-width="14" opacity="0.72"/>',
    };
  }
  if (normalized.includes('grao') || normalized.includes('cafe')) {
    return {
      background:
        '<circle cx="520" cy="286" r="100" fill="#358F5B" opacity="0.85"/><circle cx="102" cy="112" r="74" fill="#F23B3B" opacity="0.86"/>',
      shape:
        '<ellipse cx="286" cy="188" rx="178" ry="86" fill="#FFF7D7"/><path d="M205 186c42-74 116-74 158 0-42 74-116 74-158 0z" fill="#F07820"/><path d="M284 124c-20 34-20 94 0 128" fill="none" stroke="#232323" stroke-width="18" stroke-linecap="round" opacity="0.72"/>',
    };
  }
  if (normalized.includes('nozes') || normalized.includes('semente') || normalized.includes('frutas secas')) {
    return {
      background:
        '<circle cx="520" cy="84" r="88" fill="#358F5B" opacity="0.82"/><circle cx="96" cy="292" r="108" fill="#F07820" opacity="0.72"/>',
      shape:
        '<circle cx="248" cy="198" r="58" fill="#FFF7D7"/><circle cx="336" cy="184" r="64" fill="#F07820"/><circle cx="410" cy="220" r="46" fill="#FFF7D7"/><path d="M310 142c22 28 28 62 8 100" stroke="#232323" stroke-width="12" opacity="0.55" fill="none" stroke-linecap="round"/>',
    };
  }
  if (normalized.includes('latic') || normalized.includes('creme')) {
    return {
      background:
        '<circle cx="548" cy="112" r="84" fill="#52B9EB" opacity="0.8"/><circle cx="92" cy="284" r="112" fill="#FFF7D7" opacity="0.42"/>',
      shape:
        '<path d="M250 88h118l34 70v122H214V158z" fill="#FFF7D7"/><path d="M238 156h140" stroke="#F07820" stroke-width="22" stroke-linecap="round"/><path d="M250 88h118l-24 46h-70z" fill="#52B9EB" opacity="0.88"/>',
    };
  }
  if (normalized.includes('fruta') || normalized.includes('hort')) {
    return {
      background:
        '<circle cx="536" cy="94" r="76" fill="#F23B3B" opacity="0.86"/><circle cx="104" cy="276" r="108" fill="#358F5B" opacity="0.78"/>',
      shape:
        '<circle cx="258" cy="196" r="82" fill="#F07820"/><circle cx="368" cy="196" r="82" fill="#FFF7D7"/><path d="M310 96c44 6 76 28 96 66" fill="none" stroke="#358F5B" stroke-width="22" stroke-linecap="round"/>',
    };
  }
  if (normalized.includes('legume') || normalized.includes('verdura')) {
    return {
      background:
        '<circle cx="534" cy="96" r="80" fill="#358F5B" opacity="0.88"/><circle cx="96" cy="292" r="110" fill="#52B9EB" opacity="0.58"/>',
      shape:
        '<path d="M208 234c22-92 106-132 190-96 34 14 58 48 54 84-72 52-172 64-244 12z" fill="#FFF7D7"/><path d="M284 134c24-50 72-54 108-34" fill="none" stroke="#358F5B" stroke-width="22" stroke-linecap="round"/><path d="M250 218h160" stroke="#F07820" stroke-width="18" stroke-linecap="round"/>',
    };
  }
  if (normalized.includes('molho') || normalized.includes('condimento')) {
    return {
      background:
        '<circle cx="528" cy="94" r="84" fill="#F23B3B" opacity="0.88"/><circle cx="94" cy="292" r="108" fill="#EDE0B4" opacity="0.52"/>',
      shape:
        '<path d="M264 78h96l18 54v146c0 22-18 40-40 40h-52c-22 0-40-18-40-40V132z" fill="#FFF7D7"/><rect x="264" y="172" width="96" height="78" rx="18" fill="#F23B3B"/><path d="M282 78h60v-24h-60z" fill="#F07820"/>',
    };
  }
  if (normalized.includes('proteina') || normalized.includes('carne')) {
    return {
      background:
        '<circle cx="520" cy="90" r="88" fill="#F23B3B" opacity="0.84"/><circle cx="94" cy="294" r="104" fill="#F07820" opacity="0.74"/>',
      shape:
        '<path d="M168 202c44-92 178-118 268-46 40 32 38 92-8 116-92 50-226 22-260-70z" fill="#FFF7D7"/><circle cx="264" cy="194" r="30" fill="#F23B3B" opacity="0.9"/>',
    };
  }
  if (normalized.includes('semi') || normalized.includes('preparado')) {
    return {
      background:
        '<circle cx="520" cy="82" r="84" fill="#52B9EB" opacity="0.75"/><circle cx="92" cy="290" r="108" fill="#F07820" opacity="0.75"/>',
      shape:
        '<rect x="166" y="126" width="304" height="138" rx="32" fill="#FFF7D7"/><path d="M200 126h236v-34H200z" fill="#F07820"/><path d="M224 176h188M224 216h126" stroke="#232323" stroke-width="16" opacity="0.55" stroke-linecap="round"/>',
    };
  }
  if (normalized.includes('tempero') || normalized.includes('especiaria')) {
    return {
      background:
        '<circle cx="530" cy="96" r="84" fill="#F07820" opacity="0.8"/><circle cx="94" cy="290" r="110" fill="#358F5B" opacity="0.7"/>',
      shape:
        '<circle cx="246" cy="214" r="30" fill="#FFF7D7"/><circle cx="314" cy="178" r="22" fill="#FFF7D7"/><circle cx="384" cy="220" r="34" fill="#FFF7D7"/><path d="M210 250c70 34 152 30 218-4" stroke="#F07820" stroke-width="22" stroke-linecap="round" fill="none"/>',
    };
  }
  if (normalized.includes('oleo') || normalized.includes('gordura')) {
    return {
      background:
        '<circle cx="526" cy="92" r="86" fill="#52B9EB" opacity="0.68"/><circle cx="94" cy="292" r="110" fill="#F07820" opacity="0.82"/>',
      shape:
        '<path d="M318 76c70 82 106 134 106 180 0 50-40 78-106 78s-106-28-106-78c0-46 36-98 106-180z" fill="#FFF7D7"/><path d="M318 146c34 44 50 76 50 104 0 26-20 42-50 42s-50-16-50-42c0-28 16-60 50-104z" fill="#F07820"/>',
    };
  }
  return {
    background:
      '<circle cx="522" cy="90" r="82" fill="#F07820" opacity="0.88"/><circle cx="104" cy="292" r="108" fill="#52B9EB" opacity="0.68"/>',
    shape:
      '<rect x="162" y="116" width="300" height="164" rx="36" fill="#FFF7D7"/><path d="M206 164h212M206 214h156" stroke="#F07820" stroke-width="24" stroke-linecap="round"/>',
  };
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
  pageSize,
  total,
  totalPages,
  onPageChange,
  onPageSizeChange,
}: {
  orders: FornecedorOrder[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
}) {
  return (
    <DataTable
      headers={orderHeaders}
      colSpan={5}
      minWidth="720px"
      isEmpty={orders.length === 0}
      emptyMessage="Nenhum pedido registrado."
      embedded
      pagination={{
        page,
        pageSize,
        total,
        totalPages,
        onPageChange,
        onPageSizeChange,
        pageSizeOptions: ORDER_PAGE_SIZE_OPTIONS,
      }}
    >
      {orders.map((order) => (
        <tr
          key={order.id}
          className="border-b border-stone-100 transition-colors last:border-0 hover:bg-stone-50"
        >
          <BodyCell strong>{order.id}</BodyCell>
          <BodyCell>{fmt.date(order.order_date)}</BodyCell>
          <BodyCell>{fmt.number(order.items_qty, 2)}</BodyCell>
          <BodyCell>{fmt.currency(order.total_value)}</BodyCell>
          <BodyCell align="center">
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
  { key: 'qty', content: 'Quantidade' },
  { key: 'value', content: 'Valor total' },
  { key: 'status', content: 'Status', align: 'center' },
];

function StatusPill({ status }: { status: string }) {
  const delivered = status.toLowerCase() === 'entregue';
  return (
    <span
      className={[
        'inline-flex rounded-full border px-2.5 py-1 text-xs font-bold',
        delivered
          ? 'border-emerald-100 bg-emerald-50 text-emerald-700'
          : 'border-amber-100 bg-amber-50 text-amber-700',
      ].join(' ')}
    >
      {formatStatus(status)}
    </span>
  );
}

function formatStatus(status: string) {
  const normalized = status.toLowerCase().replace(/_/g, ' ');
  if (normalized === 'em transito') return 'Em trânsito';
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

function formatDocument(value?: string | null) {
  const digits = value?.replace(/\D/g, '') ?? '';
  if (digits.length !== 14) return formatEmpty(value);
  return digits.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5');
}

function formatPhone(value?: string | null) {
  const digits = value?.replace(/\D/g, '') ?? '';
  if (digits.length === 10) {
    return digits.replace(/^(\d{2})(\d{4})(\d{4})$/, '($1) $2-$3');
  }
  if (digits.length === 11) {
    return digits.replace(/^(\d{2})(\d{5})(\d{4})$/, '($1) $2-$3');
  }
  return formatEmpty(value);
}
