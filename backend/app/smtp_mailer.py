import html
import os
import smtplib
from dataclasses import dataclass
from datetime import date
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

MAESTRO_LOGO_PATH = (
    Path(__file__).resolve().parents[2]
    / "frontend"
    / "public"
    / "images"
    / "maestro-logo.svg"
)
MAESTRO_LOGO_CID = "maestro-logo"


@dataclass(frozen=True)
class OrderEmailItem:
    name: str
    qty: float
    unit: str
    unit_price: float
    total_value: float


@dataclass(frozen=True)
class OrderEmail:
    supplier_name: str
    supplier_email: str
    order_date: date
    expected_date: date
    items: list[OrderEmailItem]


@dataclass(frozen=True)
class SmtpSettings:
    host: str
    port: int
    username: str | None
    password: str | None
    from_email: str
    from_name: str
    use_tls: bool
    timeout_seconds: float


def get_smtp_settings() -> SmtpSettings | None:
    enabled = os.getenv("SMTP_ENABLED", "1").strip().lower()
    if enabled in {"0", "false", "no", "off"}:
        return None

    host = os.getenv("SMTP_HOST", "localhost").strip()
    from_email = os.getenv("SMTP_FROM_EMAIL", "pedidos@saltim.local").strip()
    if not host or not from_email:
        return None

    return SmtpSettings(
        host=host,
        port=int(os.getenv("SMTP_PORT", "1025")),
        username=os.getenv("SMTP_USER") or os.getenv("SMTP_USERNAME") or None,
        password=os.getenv("SMTP_PASSWORD") or None,
        from_email=from_email,
        from_name=os.getenv("SMTP_FROM_NAME", "Saltim Café"),
        use_tls=os.getenv("SMTP_USE_TLS", "0").strip().lower()
        not in {"0", "false", "no", "off"},
        timeout_seconds=float(os.getenv("SMTP_TIMEOUT_SECONDS", "10")),
    )


def send_order_email(order: OrderEmail, settings: SmtpSettings) -> None:
    message = EmailMessage()
    message["Subject"] = (
        f"Maestro | Pedido de compra - {order.order_date.isoformat()} - {order.supplier_name}"
    )
    message["From"] = formataddr((settings.from_name, settings.from_email))
    message["To"] = formataddr((order.supplier_name, order.supplier_email))
    message.set_content(_plain_body(order))
    message.add_alternative(_html_body(order), subtype="html")
    _attach_logo(message)

    with smtplib.SMTP(
        settings.host,
        settings.port,
        timeout=settings.timeout_seconds,
    ) as smtp:
        if settings.use_tls:
            smtp.starttls()
        if settings.username and settings.password:
            smtp.login(settings.username, settings.password)
        smtp.send_message(message)


def _attach_logo(message: EmailMessage) -> None:
    if not MAESTRO_LOGO_PATH.exists():
        return
    payload = message.get_payload()
    if not isinstance(payload, list) or len(payload) < 2:
        return
    html_part = payload[1]
    html_part.add_related(
        MAESTRO_LOGO_PATH.read_bytes(),
        maintype="image",
        subtype="svg+xml",
        cid=f"<{MAESTRO_LOGO_CID}>",
        filename="maestro-logo.svg",
    )


def _plain_body(order: OrderEmail) -> str:
    total = sum(item.total_value for item in order.items)
    lines = [
        f"Olá, {order.supplier_name}.",
        "",
        "Segue pedido de compra via Maestro:",
        f"Data do pedido: {_format_date(order.order_date)}",
        f"Previsao de entrega: {_format_date(order.expected_date)}",
        "",
        "Itens:",
    ]
    for item in order.items:
        lines.append(
            "- "
            f"{item.name}: {_format_number(item.qty)} {item.unit} "
            f"(unitario {_format_currency(item.unit_price)}, total {_format_currency(item.total_value)})"
        )
    lines.extend(
        [
            "",
            f"Total estimado: {_format_currency(total)}",
            "",
            "Obrigado,",
            "Equipe Maestro",
        ]
    )
    return "\n".join(lines)


def _format_number(value: float) -> str:
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _format_currency(value: float) -> str:
    return f"R$ {_format_number(value)}"


def _format_date(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def _html_body(order: OrderEmail) -> str:
    total = sum(item.total_value for item in order.items)
    rows = "\n".join(
        (
            '<tr style="border-bottom:1px solid #ede9fe">'
            '<td style="padding:14px 16px;color:#211f33;font-weight:700">'
            f"{html.escape(item.name)}"
            "</td>"
            '<td style="padding:14px 12px;text-align:right;color:#514a6a;font-weight:700;white-space:nowrap">'
            f"{_format_number(item.qty)}"
            "</td>"
            '<td style="padding:14px 12px;color:#6f6787;text-transform:uppercase;font-size:12px;font-weight:800;letter-spacing:.04em">'
            f"{html.escape(item.unit)}"
            "</td>"
            '<td style="padding:14px 12px;text-align:right;color:#514a6a;white-space:nowrap">'
            f"{_format_currency(item.unit_price)}"
            "</td>"
            '<td style="padding:14px 16px;text-align:right;color:#1b1464;font-weight:900;white-space:nowrap">'
            f"{_format_currency(item.total_value)}"
            "</td>"
            "</tr>"
        )
        for item in order.items
    )
    return f"""
<!doctype html>
<html lang="pt-BR">
  <body style="margin:0;padding:0;background:#f6f5fb;font-family:Arial,'Helvetica Neue',sans-serif;color:#211f33">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f6f5fb;padding:28px 12px">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:760px;background:#ffffff;border:1px solid #e4e0ef;border-radius:18px;overflow:hidden">
            <tr>
              <td style="background:#1b1464;padding:28px 32px">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                  <tr>
                    <td>
                      <table role="presentation" cellspacing="0" cellpadding="0">
                        <tr>
                          <td style="padding-right:12px;vertical-align:middle;color:white">
                            <img src="cid:{MAESTRO_LOGO_CID}" width="42" height="31" alt="Maestro" style="display:block;border:0;outline:none;text-decoration:none;color:white;">
                          </td>
                          <td style="vertical-align:middle">
                            <div style="font-size:12px;font-weight:900;letter-spacing:.16em;text-transform:uppercase;color:#ffbd9c">Maestro</div>
                            <div style="font-size:11px;color:#ded9ff;font-weight:700;letter-spacing:.06em;text-transform:uppercase">Compras & Suprimentos</div>
                          </td>
                        </tr>
                      </table>
                      <h1 style="margin:8px 0 0;font-size:28px;line-height:1.15;color:#ffffff">Pedido de compra</h1>
                      <p style="margin:10px 0 0;color:#ded9ff;font-size:14px">Olá, {html.escape(order.supplier_name)}. Segue o pedido para separação e entrega.</p>
                    </td>
                    <td align="right" style="vertical-align:top">
                      <div style="display:inline-block;background:#f15a24;color:#ffffff;border-radius:999px;padding:9px 14px;font-size:12px;font-weight:900;white-space:nowrap">
                        Total: {_format_currency(total)}
                      </div>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:24px 32px 8px">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                  <tr>
                    <td width="50%" style="padding:0 8px 12px 0">
                      <div style="background:#efedff;border:1px solid #ded9ff;border-radius:14px;padding:16px">
                        <div style="font-size:11px;font-weight:900;letter-spacing:.08em;text-transform:uppercase;color:#6f6787">Data do pedido</div>
                        <div style="margin-top:6px;font-size:20px;font-weight:900;color:#1b1464">{_format_date(order.order_date)}</div>
                      </div>
                    </td>
                    <td width="50%" style="padding:0 0 12px 8px">
                      <div style="background:#fff2ec;border:1px solid #ffbd9c;border-radius:14px;padding:16px">
                        <div style="font-size:11px;font-weight:900;letter-spacing:.08em;text-transform:uppercase;color:#8d3214">Previsão de entrega</div>
                        <div style="margin-top:6px;font-size:20px;font-weight:900;color:#f15a24">{_format_date(order.expected_date)}</div>
                      </div>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:8px 32px 28px">
                <table width="100%" cellspacing="0" cellpadding="0" style="border-collapse:separate;border-spacing:0;border:1px solid #e4e0ef;border-radius:14px;overflow:hidden">
                  <thead>
                    <tr style="background:#f1eff7">
                      <th align="left" style="padding:13px 16px;color:#514a6a;font-size:11px;text-transform:uppercase;letter-spacing:.08em">Item</th>
                      <th align="right" style="padding:13px 12px;color:#514a6a;font-size:11px;text-transform:uppercase;letter-spacing:.08em">Qtd</th>
                      <th align="left" style="padding:13px 12px;color:#514a6a;font-size:11px;text-transform:uppercase;letter-spacing:.08em">Un.</th>
                      <th align="right" style="padding:13px 12px;color:#514a6a;font-size:11px;text-transform:uppercase;letter-spacing:.08em">Unit.</th>
                      <th align="right" style="padding:13px 16px;color:#514a6a;font-size:11px;text-transform:uppercase;letter-spacing:.08em">Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows}
                  </tbody>
                  <tfoot>
                    <tr style="background:#1b1464">
                      <td colspan="4" style="padding:16px;text-align:right;color:#ded9ff;font-size:13px;font-weight:900;text-transform:uppercase;letter-spacing:.08em">Total estimado</td>
                      <td style="padding:16px;text-align:right;color:#ffffff;font-size:18px;font-weight:900;white-space:nowrap">{_format_currency(total)}</td>
                    </tr>
                  </tfoot>
                </table>
                <div style="margin-top:18px;background:#fbfafc;border-left:4px solid #f15a24;border-radius:12px;padding:14px 16px;color:#514a6a;font-size:13px;line-height:1.55">
                  Caso algum item precise de ajuste, responda este email informando o item e a quantidade disponível.
                </div>
              </td>
            </tr>
            <tr>
              <td style="padding:0 32px 30px">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-top:1px solid #e4e0ef;padding-top:22px">
                  <tr>
                    <td style="width:58px;vertical-align:top">
                      <div style="width:46px;height:46px;border-radius:14px;background:#1b1464;text-align:center;line-height:46px">
                        <img src="cid:{MAESTRO_LOGO_CID}" width="28" height="20" alt="M" style="display:inline-block;vertical-align:middle;border:0">
                      </div>
                    </td>
                    <td style="vertical-align:top;color:#514a6a;font-size:12px;line-height:1.55">
                      <div style="font-size:14px;font-weight:900;color:#1b1464">Equipe Maestro</div>
                      <div style="font-weight:800;color:#f15a24">Compras, Estoque & Operações</div>
                      <div style="margin-top:8px;color:#6f6787">
                        Maestro para Saltim Café<br>
                        Gestão inteligente de pedidos, fornecedores e reposição de estoque.
                      </div>
                      <div style="margin-top:10px;font-size:11px;color:#9b93b2">
                        Esta mensagem foi gerada automaticamente. Responda este email para alinhar disponibilidade, substituições ou ajustes de entrega.
                      </div>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:16px 32px;background:#f1eff7;color:#6f6787;font-size:11px;line-height:1.5">
                <strong style="color:#1b1464">Maestro</strong> · Relatório transacional de compra · Confidencial para o fornecedor destinatário
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""
