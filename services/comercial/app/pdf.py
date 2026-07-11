"""E2-H2: generación de la cotización en PDF con el formato oficial.

No es texto libre: el layout (logo, datos del cliente, desglose de
anticipos, número de cotización) es fijo y lo arma esta función a partir
de los datos capturados en el formulario.
"""
from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.models import Lead, Quotation


def _money(value: int) -> str:
    return f"${value:,.0f}".replace(",", ".")


def build_quotation_pdf(lead: Lead, quotation: Quotation) -> bytes:
    buffer = BytesIO()
    doc = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    y = height - 60
    doc.setFont("Helvetica-Bold", 18)
    doc.drawString(50, y, "Grupo Mactral")
    doc.setFont("Helvetica", 10)
    doc.drawString(50, y - 16, "Plataforma de Gestión de Proyectos")

    doc.setFont("Helvetica-Bold", 14)
    doc.drawRightString(width - 50, y, f"Cotización {lead.codigo}")
    doc.setFont("Helvetica", 10)
    doc.drawRightString(width - 50, y - 16, f"Versión v{quotation.version}")

    y -= 60
    doc.setFont("Helvetica-Bold", 11)
    doc.drawString(50, y, "Datos del cliente")
    doc.setFont("Helvetica", 10)
    y -= 18
    doc.drawString(50, y, f"Cliente: {lead.nombre}")
    y -= 14
    doc.drawString(50, y, f"Ciudad: {lead.ciudad}")

    y -= 30
    doc.setFont("Helvetica-Bold", 11)
    doc.drawString(50, y, "Descripción del equipo")
    doc.setFont("Helvetica", 10)
    y -= 18
    doc.drawString(50, y, f"Producto: {lead.tipo_producto}")
    y -= 14
    doc.drawString(50, y, f"Marca: {lead.marca}")
    y -= 14
    doc.drawString(50, y, f"Tipo de pago: {quotation.tipo_pago.value.title()}")
    y -= 14
    doc.drawString(
        50, y, f"Fecha estimada de entrega: {quotation.fecha_estimada_entrega.strftime('%d/%m/%Y')}"
    )

    y -= 30
    doc.setFont("Helvetica-Bold", 11)
    doc.drawString(50, y, "Desglose de anticipos")
    doc.setFont("Helvetica", 10)

    anticipo_1 = round(quotation.valor_equipo * quotation.anticipo_inicial_pct / 100)
    anticipo_2 = round(quotation.valor_equipo * quotation.segundo_anticipo_pct / 100)
    saldo_final = round(quotation.valor_equipo * quotation.saldo_final_pct / 100)

    filas = [
        (f"Anticipo 1 ({quotation.anticipo_inicial_pct}%)", anticipo_1),
        (f"Anticipo 2 ({quotation.segundo_anticipo_pct}%)", anticipo_2),
        (f"Saldo final ({quotation.saldo_final_pct}%)", saldo_final),
    ]
    for label, amount in filas:
        y -= 18
        doc.drawString(50, y, label)
        doc.drawRightString(width - 50, y, _money(amount))

    y -= 24
    doc.setFont("Helvetica-Bold", 11)
    doc.drawString(50, y, "Total contrato")
    doc.drawRightString(width - 50, y, _money(quotation.valor_equipo))

    doc.showPage()
    doc.save()
    return buffer.getvalue()
