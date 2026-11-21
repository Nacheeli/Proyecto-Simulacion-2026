# Malla antigranizo, seguro o nada: simulación para decidir

Proyecto final de **Simulación – UTN FRSR 2026**.

Un productor de vid de Rama Caída (San Rafael, Mendoza) tiene que elegir cómo protegerse del granizo.
El simulador reproduce 20 años de producción con Monte Carlo y compara tres alternativas por VAN
esperado y por riesgo:

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
app.py                  Interfaz (tkinter + matplotlib): panel de datos + 4 pestañas
verificar.py            Reporte de verificación para el informe
data/
  granizo_san_rafael_aero_1974_2024.csv   Serie real de días con granizo
simulador/              Lógica del modelo (importable, sin interfaz)
  datos_reales.py       DATOS REALES con su fuente
  supuestos.py          SUPUESTOS editables (datos pendientes)
  parametros.py         Parámetros de una corrida (reales + supuestos)
  generador.py          Módulo 1 – congruencial lineal + prueba chi-cuadrado    (TP2)
  clima.py              Módulos 2 y 3 – Markov G/S + tabla empírica de días       (TP5, TP4)
  danio.py              Módulo 4 – daño continuo por evento y combinación         (TP4)
  finca.py              Módulo 5 – escenario de 20 años, resultado anual y VAN    (TP4)
  montecarlo.py         Módulo 6 – 10.000 réplicas e indicadores                  (TP7)
  sensibilidad.py       Módulo 7 – precio, mapa ha × frecuencia, persistencia     (TP6)
tests/test_modelo.py    Pruebas: casos a mano, frecuencias, VAN, semilla
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
supera a la media (1,40). Un multiplicador de granizadas (por defecto 1) escala la cantidad de
eventos de cada año con redondeo estocástico, para la sensibilidad.

**Daño.** El daño de cada granizada sale de una distribución **SUPUESTA continua por intervalos**
(0 %, 0–10, 10–20, 20–40, 40–60, 60–80 y 80–100 %): un número aleatorio elige el intervalo y la
posición dentro de él (transformada inversa de una función de distribución lineal por tramos). Los
daños del año se combinan como lo hace el Fondo: `1 − (1−d1)(1−d2)…`. La malla reduce cada
granizada en un 90 % (**SUPUESTO**).

**Finca.** 5,3 ha, rendimiento uniforme entre 7.100 y 7.600 kg/ha (INV). Resultado del año en pesos
constantes:

| Alternativa | Resultado del año |
|---|---|
| Sin protección | ha·rend·precio·(1−daño) − costo de producción |
| Fondo Compensador | lo anterior − aporte + compensación (si el daño es ≥ 50 %, configurable a > 50 %) |
| Malla | ha·rend·precio·(1−daño con malla) − costo de producción − pagos de la malla |

**VAN.** Indicador principal. Tasa de descuento real 5 % (**SUPUESTO**). Los resultados se
descuentan como flujos de fin de año; la compra al contado de la malla, al inicio del año. La malla
"amortizada" paga cada año el **costo anual equivalente** a la tasa de descuento, por eso las tres
formas de pago (amortizado, contado con reposición y valor residual, financiado) dan el mismo VAN
cuando la tasa del crédito es igual a la de descuento.

**Monte Carlo.** 10.000 réplicas de 20 años. Las tres alternativas se evalúan sobre **los mismos**
escenarios de clima (números aleatorios comunes). Indicadores: media, desvío y P5 del VAN, suma sin
descontar, % de años con pérdida y peor año.

**Decisión (pestaña 4).** Rentabilidad contra riesgo (VAN medio vs P5), sensibilidad al precio de la
uva, mapa de la mejor alternativa según hectáreas (1–30) y multiplicador de granizadas (0,5–2), y
experimento de persistencia (Markov real contra años independientes con la misma proporción de G).
**Criterio de mejor:** el mayor VAN medio entre las alternativas cuyo P5 del VAN es mayor que 0
(configurable).

## Datos reales y supuestos

Los valores reales están en `simulador/datos_reales.py` y los supuestos en `simulador/supuestos.py`.
En la interfaz los reales se marcan con **(R)** y los supuestos con **(S)**.

| Dato | Valor | Origen |
|---|---|---|
| Días con granizo por año, matriz de Markov | serie 1974–2024 | REAL – tutiempo.net, San Rafael Aero 87509 |
| Hectáreas, rendimiento | 5,3 ha; 7.100–7.600 kg/ha | REAL – INV Informe Área Sur 2016 |
| Fondo: aporte, compensación, umbral | $51.000/ha; $2.000.000/ha; 50 % | REAL – Gob. de Mendoza 2025-26 |
| Malla: costo y vida útil | USD 4.250/ha (rango 4.000–4.500); 15 años (rango 12–20) | REAL (rango) – MDZ 2024 |
| Tabla de daño por granizada | continua por intervalos, 0 % a 100 % | **SUPUESTO**, calibrado con DACC |
| Superficie cultivada Oasis Sur | 60.000 ha | **SUPUESTO** (para la referencia DACC) |
| Precio de la uva | $400/kg | **SUPUESTO** |
| Costo de producción | $2.200.000/ha/año | **SUPUESTO** |
| Tipo de cambio | $1.450/USD | **SUPUESTO** |
| Tasa de descuento real | 5 % anual | **SUPUESTO** |
| Compensación del Fondo | proporcional al daño | **SUPUESTO** (proporcional / fijo) |
| Condición de pago del Fondo | daño ≥ 50 % | **SUPUESTO** (las fuentes se contradicen: ≥ / >) |
| Eficacia de la malla | 90 % | **SUPUESTO** |
| Pago de la malla | amortizado (costo anual equivalente); opciones contado / financiado 8 %, 5 cuotas | **SUPUESTO** |

**Calibración del daño.** Con la tabla supuesta la pérdida media anual simulada es 13,1 %. La
referencia DACC para el Oasis Sur (5.000 a 11.000 ha llevadas al 100 % por año sobre 60.000 ha
cultivadas) da 8,3 % a 18,3 %.

**Supuesto más influyente.** Con la tabla de daño actual el Fondo paga en promedio 2,8 veces lo que
la finca aporta (P(cobrar) ≈ 10 % por año). Por eso el Fondo resulta la mejor alternativa en casi todos
los escenarios. Ese cociente depende sobre todo de la cola de la tabla de daño (años con daño ≥ 50 %).
