import numpy as np
import pandas as pd

from sklearn.linear_model import LinearRegression

from myApp.models import Exportacion


def predecir_exportaciones():

    exportaciones = list(
        Exportacion.objects.all().order_by("id")
    )

    if len(exportaciones) < 2:
        return "Datos insuficientes"

    x = np.array(
        range(len(exportaciones))
    ).reshape(-1, 1)

    y = np.array(
        [1 for _ in exportaciones]
    )

    modelo = LinearRegression()

    modelo.fit(x, y)

    siguiente = np.array(
        [[len(exportaciones)]]
    )

    prediccion = modelo.predict(
        siguiente
    )[0]

    return round(float(prediccion), 2)