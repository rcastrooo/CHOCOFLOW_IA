import pandas as pd

from myApp.models import Produccion


def analizar_rendimiento():

    datos = []

    for p in Produccion.objects.all():

        datos.append({
            "empleado": p.empleado_responsable.nombre
        })

    if not datos:

        return {}

    df = pd.DataFrame(datos)

    conteo = (
        df["empleado"]
        .value_counts()
        .reset_index()
    )

    mejor = conteo.iloc[0]
    peor = conteo.iloc[-1]

    return {
        "mejor_empleado": mejor["empleado"],
        "producciones_mejor": int(mejor["count"]),
        "peor_empleado": peor["empleado"],
        "producciones_peor": int(peor["count"])
    }