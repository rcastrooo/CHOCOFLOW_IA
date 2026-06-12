from datetime import date, timedelta

from myApp.models import Lote, Exportacion


def detectar_vencimientos_lotes():
    alertas = []

    hoy = date.today()
    limite = hoy + timedelta(days=15)

    lotes = Lote.objects.filter(
        fecha_vencimiento__lte=limite
    )

    for lote in lotes:

        dias = (lote.fecha_vencimiento - hoy).days

        if dias < 0:
            alertas.append(
                f"El lote {lote.codigo_lote} ya está vencido."
            )

        else:
            alertas.append(
                f"El lote {lote.codigo_lote} vence en {dias} días."
            )

    return alertas


def detectar_retrasos_exportaciones():

    alertas = []

    hoy = date.today()

    exportaciones = Exportacion.objects.exclude(
        estado='Entregado'
    )

    for e in exportaciones:

        if e.fecha_entrega < hoy:

            alertas.append(
                f"Exportación a {e.pais} presenta retraso."
            )

    return alertas