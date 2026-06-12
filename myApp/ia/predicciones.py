from sklearn.linear_model import LinearRegression
from myApp.models import Produccion
import pandas as pd
import numpy as np


def predecir_proxima_produccion():

    producciones = Produccion.objects.all().order_by('id')

    if producciones.count() < 2:
        return None

    datos = []

    for i, p in enumerate(producciones):
        try:
            datos.append([
                i + 1,
                float(p.cantidad_requerida)
            ])
        except:
            pass

    if len(datos) < 2:
        return None

    df = pd.DataFrame(
        datos,
        columns=['periodo', 'cantidad']
    )

    X = df[['periodo']]
    y = df['cantidad']

    modelo = LinearRegression()
    modelo.fit(X, y)

    siguiente_periodo = np.array([[len(df) + 1]])

    prediccion = modelo.predict(
        siguiente_periodo
    )[0]

    return round(prediccion, 2)