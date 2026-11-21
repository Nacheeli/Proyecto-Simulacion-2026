# Malla antigranizo, seguro o nada: simulación para decidir

Proyecto final de **Simulación – UTN FRSR 2026**.

Un productor de vid de Rama Caída (San Rafael, Mendoza) tiene que elegir cómo protegerse del granizo.
El simulador reproduce 20 años de producción con Monte Carlo y compara tres alternativas por ganancia
esperada y por riesgo:

1. **Sin protección**
2. **Fondo Compensador Agrícola** (cobertura específica granizo, Oasis Sur)
3. **Malla antigranizo**

## Cómo ejecutarlo

```bash
pip install -r requirements.txt
python app.py          # interfaz gráfica
python verificar.py    # reporte de verificación por consola
python -m pytest       # pruebas automáticas
```

Requiere Python 3.10 o posterior (tkinter viene incluido en el instalador de Windows).

## Estructura

```
app.py                  Interfaz (tkinter + matplotlib): panel de datos + pestañas
verificar.py            Reporte de verificación para el informe
data/
  granizo_san_rafael_aero_1974_2024.csv   Serie real de días con granizo
simulador/              Lógica del modelo (importable, sin interfaz)
  datos_reales.py       DATOS REALES con su fuente
  supuestos.py          SUPUESTOS editables (datos pendientes)
  parametros.py         Parámetros de una corrida (reales + supuestos)
  generador.py          Módulo 1 – congruencial lineal + prueba chi-cuadrado   (TP2)
  clima.py              Módulos 2 y 3 – Markov G/S + tabla empírica de días      (TP5, TP4)
  danio.py              Módulo 4 – daño por evento y combinación                 (TP4)
  finca.py              Módulo 5 – escenario de 20 años y resultado de cada alternativa (TP4)
  montecarlo.py         Módulo 6 – 10.000 réplicas e indicadores                 (TP7)
tests/test_modelo.py    Pruebas: casos a mano, frecuencias, semilla
```

## Modelo

**Números aleatorios.** Congruencial lineal mixto `X(n+1) = (a·X(n) + c) mod m` con
a = 1.664.525, c = 1.013.904.223, m = 2³² (período completo por Hull–Dobell). Todo el proyecto usa
este generador. Prueba de frecuencias chi-cuadrado con 10 intervalos y α = 0,05.

**Clima.** Cadena de Markov año con granizo (G) / sin granizo (S) con la matriz real de
San Rafael Aero: S→S 0,80, S→G 0,20, G→S 0,11, G→G 0,89. El primer año se sortea con la
distribución estacionaria.

**Granizadas por año.** Si el año es S hay 0 días. Si es G, los días se sortean por transformada
inversa de la tabla real de 1 a 7 días, renormalizada. No se usa Poisson porque la varianza (2,33)
supera a la media (1,40). Así la cadena fija cuántos años tienen granizo y la tabla real fija cuántas
granizadas hay en esos años.

**Daño.** Cada granizada tiene un daño sorteado de una tabla **SUPUESTA**. Los daños del año se
combinan como lo hace el Fondo: `1 − (1−d1)(1−d2)…`. La malla reduce cada granizada en un 90 %
(**SUPUESTO**).

**Finca.** 5,3 ha, rendimiento uniforme entre 7.100 y 7.600 kg/ha (INV). Resultado del año en pesos
constantes:

| Alternativa | Resultado del año |
|---|---|
| Sin protección | ha·rend·precio·(1−daño) − costo de producción |
| Fondo Compensador | lo anterior − aporte + compensación (solo si el daño **supera** el 50 %) |
| Malla | ha·rend·precio·(1−daño con malla) − costo de producción − costo de la malla |

**Monte Carlo.** 10.000 réplicas de 20 años. Las tres alternativas se evalúan sobre **los mismos**
escenarios de clima (números aleatorios comunes). Indicadores: media, desvío y P5 de la ganancia de
20 años, % de años con pérdida y peor año.

## Datos reales y supuestos

Los valores reales están en `simulador/datos_reales.py` y los supuestos en `simulador/supuestos.py`.
En la interfaz los reales se marcan con **(R)** y los supuestos con **(S)**.

| Dato | Valor | Origen |
|---|---|---|
| Días con granizo por año, matriz de Markov | serie 1974–2024 | REAL – tutiempo.net, San Rafael Aero 87509 |
| Hectáreas, rendimiento | 5,3 ha; 7.100–7.600 kg/ha | REAL – INV Informe Área Sur 2016 |
| Fondo: aporte, compensación, umbral | $51.000/ha; $2.000.000/ha; 50 % | REAL – Gob. de Mendoza 2025-26 |
| Malla: costo y vida útil | USD 4.250/ha (rango 4.000–4.500); 15 años (rango 12–20) | REAL (rango) – MDZ 2024 |
| Tabla de daño por granizada | 0 % a 90 % | **SUPUESTO**, calibrado con DACC |
| Superficie cultivada Oasis Sur | 60.000 ha | **SUPUESTO** (para la referencia DACC) |
| Precio de la uva | $400/kg | **SUPUESTO** |
| Costo de producción | $2.200.000/ha/año | **SUPUESTO** |
| Tipo de cambio | $1.450/USD | **SUPUESTO** |
| Compensación del Fondo | proporcional al daño | **SUPUESTO** (configurable: proporcional / fijo) |
| Eficacia de la malla | 90 % | **SUPUESTO** |
| Pago de la malla | amortizado (configurable: contado / financiado, 8 %, 5 cuotas) | **SUPUESTO** |

**Calibración del daño.** Con la tabla supuesta la pérdida media anual simulada es ≈ 13 %. La
referencia DACC para el Oasis Sur (5.000 a 11.000 ha llevadas al 100 % por año sobre 60.000 ha
cultivadas) da 8,3 % a 18,3 %.

## Alcance de esta versión

Módulos 1 a 6 y pestañas 1 a 3. Para la segunda iteración quedan la sensibilidad (barrido de hectáreas
y frecuencia de granizo) y la pestaña 4 (Decisión).
