import pandas as pd

from sklearn.ensemble import IsolationForest

from myApp.models import Produccion


def detectar_anomalias():

    datos = []

    for p in Produccion.objects.all():

        try:

            cantidad = float(
                str(p.cantidad_requerida)
                .replace(",", ".")
            )

            datos.append(
                [cantidad]
            )

        except:
            pass

    if len(datos) < 5:
        return []

    df = pd.DataFrame(
        datos,
        columns=["cantidad"]
    )

    modelo = IsolationForest(
        contamination=0.1,
        random_state=42
    )

    resultado = modelo.fit_predict(df)

    alertas = []

    for i, valor in enumerate(resultado):

        if valor == -1:

            alertas.append(
                f"Producción anómala detectada: {datos[i][0]}"
            )

    return alertas