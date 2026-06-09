import pandas as pd

from myApp.models import (
    Empleado,
    Produccion,
    Exportacion,
    Lote
)


def obtener_resumen_empresa():

    empleados = Empleado.objects.values('estado')
    producciones = Produccion.objects.values('estado')
    exportaciones = Exportacion.objects.values('estado')
    lotes = Lote.objects.values('codigo_lote')

    df_emp = pd.DataFrame(list(empleados))
    df_prod = pd.DataFrame(list(producciones))
    df_exp = pd.DataFrame(list(exportaciones))
    df_lotes = pd.DataFrame(list(lotes))

    resumen = {
        "empleados_activos": 0,
        "empleados_suspendidos": 0,
        "producciones_proceso": 0,
        "producciones_finalizadas": 0,
        "exportaciones_pendientes": 0,
        "total_lotes": len(df_lotes)
    }

    if not df_emp.empty:
        resumen["empleados_activos"] = len(
            df_emp[df_emp["estado"] == "Activo"]
        )

        resumen["empleados_suspendidos"] = len(
            df_emp[df_emp["estado"] == "Suspendido"]
        )

    if not df_prod.empty:
        resumen["producciones_proceso"] = len(
            df_prod[df_prod["estado"] == "En Proceso"]
        )

        resumen["producciones_finalizadas"] = len(
            df_prod[df_prod["estado"] == "Finalizado"]
        )

    if not df_exp.empty:
        resumen["exportaciones_pendientes"] = len(
            df_exp[df_exp["estado"] == "Pendiente"]
        )

    return resumen


def detectar_alertas():

    resumen = obtener_resumen_empresa()

    alertas = []

    if resumen["empleados_activos"] <= 1:
        alertas.append(
            "Existe muy poco personal activo para la operación."
        )

    if resumen["exportaciones_pendientes"] >= 5:
        alertas.append(
            "Hay varias exportaciones pendientes por gestionar."
        )

    if resumen["producciones_proceso"] == 0:
        alertas.append(
            "No existen producciones en proceso actualmente."
        )

    if resumen["total_lotes"] == 0:
        alertas.append(
            "No existen lotes registrados."
        )

    return alertas