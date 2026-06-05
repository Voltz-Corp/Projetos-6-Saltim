import html
import os
import smtplib
from dataclasses import dataclass
from datetime import date
from email.message import EmailMessage
from email.utils import formataddr


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
    host = os.getenv("SMTP_HOST", "").strip()
    from_email = os.getenv("SMTP_FROM_EMAIL", "").strip()
    if not host or not from_email:
        return None

    return SmtpSettings(
        host=host,
        port=int(os.getenv("SMTP_PORT", "587")),
        username=os.getenv("SMTP_USER") or None,
        password=os.getenv("SMTP_PASSWORD") or None,
        from_email=from_email,
        from_name=os.getenv("SMTP_FROM_NAME", "Saltim Café"),
        use_tls=os.getenv("SMTP_USE_TLS", "1").strip().lower()
        not in {"0", "false", "no", "off"},
        timeout_seconds=float(os.getenv("SMTP_TIMEOUT_SECONDS", "10")),
    )


def send_order_email(order: OrderEmail, settings: SmtpSettings) -> None:
    message = EmailMessage()
    message["Subject"] = (
        f"Pedido Saltim Café - {order.order_date.isoformat()} - {order.supplier_name}"
    )
    message["From"] = formataddr((settings.from_name, settings.from_email))
    message["To"] = formataddr((order.supplier_name, order.supplier_email))
    message.set_content(_plain_body(order))
    message.add_alternative(_html_body(order), subtype="html")

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


def _plain_body(order: OrderEmail) -> str:
    total = sum(item.total_value for item in order.items)
    lines = [
        f"Olá, {order.supplier_name}.",
        "",
        "Segue pedido do Saltim Café:",
        f"Data do pedido: {order.order_date.isoformat()}",
        f"Previsao de entrega: {order.expected_date.isoformat()}",
        "",
        "Itens:",
    ]
    for item in order.items:
        lines.append(
            "- "
            f"{item.name}: {item.qty:.2f} {item.unit} "
            f"(unitario R$ {item.unit_price:.2f}, total R$ {item.total_value:.2f})"
        )
    lines.extend(
        [
            "",
            f"Total estimado: R$ {total:.2f}",
            "",
            "Obrigado,",
            "Equipe Saltim Café",
        ]
    )
    return "\n".join(lines)


def _html_body(order: OrderEmail) -> str:
    total = sum(item.total_value for item in order.items)
    rows = "\n".join(
        (
            "<tr>"
            f"<td>{html.escape(item.name)}</td>"
            f"<td style=\"text-align:right\">{item.qty:.2f}</td>"
            f"<td>{html.escape(item.unit)}</td>"
            f"<td style=\"text-align:right\">R$ {item.unit_price:.2f}</td>"
            f"<td style=\"text-align:right\">R$ {item.total_value:.2f}</td>"
            "</tr>"
        )
        for item in order.items
    )
    return f"""
<!doctype html>
<html>
  <body style="font-family: Arial, sans-serif; color: #292524; line-height: 1.5">
    <h2 style="margin-bottom: 4px">Pedido Saltim Café</h2>
    <p>Olá, {html.escape(order.supplier_name)}.</p>
    <p>Segue pedido do Saltim Café para entrega.</p>
    <p>
      <strong>Data do pedido:</strong> {order.order_date.isoformat()}<br>
      <strong>Previsao de entrega:</strong> {order.expected_date.isoformat()}
    </p>
    <table cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%; max-width: 720px">
      <thead>
        <tr style="background: #f5f5f4">
          <th align="left">Item</th>
          <th align="right">Qtd</th>
          <th align="left">Unidade</th>
          <th align="right">Valor unit.</th>
          <th align="right">Total</th>
        </tr>
      </thead>
      <tbody>
        {rows}
      </tbody>
      <tfoot>
        <tr>
          <td colspan="4" style="text-align:right"><strong>Total estimado</strong></td>
          <td style="text-align:right"><strong>R$ {total:.2f}</strong></td>
        </tr>
      </tfoot>
    </table>
    <p>Obrigado,<br>Equipe Saltim Café</p>
  </body>
</html>
"""
