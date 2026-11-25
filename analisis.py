"""Análisis reproducible del centro de datos. Todos los datos son simulados."""
from pathlib import Path
import json
import math
import platform
import numpy as np
import pandas as pd
import scipy
from scipy import stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
CONFIG = dict(semilla=4002, dias=30, horas=24, potencia_it_kw=120.0,
              sd_it_dia_kw=6.0, sd_ambiente_dia_c=2.0,
              refrigeracion_base_kw=35.0, auxiliares_base_kw=37.0,
              factor_refrigeracion_mejorada=0.60, auxiliares_mejorada_kw=27.0,
              sd_refrigeracion_dia_kw=1.8, inspecciones_dia=20,
              prob_rechazo=0.02, avisos_dia=1.5, alpha=0.05)
VARIABLES = ['p_it_kw', 'temperatura_exterior_c', 'p_refrigeracion_kw',
             'p_otros_kw', 'p_total_kw', 'pue_horario']


def generar_datos(config=CONFIG):
    """Recibe parámetros; simula 30 pares de días; devuelve horario bruto y eventos.

    Cada par comparte carga IT y ambiente. Los errores diarios son independientes
    entre pares. Las horas de un día no se tratan como observaciones independientes.
    """
    rng = np.random.default_rng(config['semilla'])
    rows = []
    for dia in range(1, config['dias'] + 1):
        it_dia = rng.normal(0, config['sd_it_dia_kw'])
        ambiente_dia = rng.normal(0, config['sd_ambiente_dia_c'])
        errores_dia = rng.normal(0, config['sd_refrigeracion_dia_kw'], 2)
        for hora in range(config['horas']):
            ciclo = np.cos(2 * np.pi * (hora - 15) / 24)
            it = config['potencia_it_kw'] + it_dia + 6 * ciclo + rng.normal(0, 1.5)
            ambiente = 24 + ambiente_dia + 5 * ciclo + rng.normal(0, 0.5)
            comun = config['refrigeracion_base_kw'] + 8 * ciclo + 0.8 * ambiente_dia + 0.08 * (it - config['potencia_it_kw']) + rng.normal(0, 0.7)
            for j, escenario in enumerate(['base', 'mejorado']):
                factor = 1 if j == 0 else config['factor_refrigeracion_mejorada']
                otros = config['auxiliares_base_kw'] if j == 0 else config['auxiliares_mejorada_kw']
                frio = factor * comun + errores_dia[j] + rng.normal(0, 0.4)
                total = it + frio + otros
                rows.append([dia, hora, escenario, it, ambiente, frio, otros, total, total / it])
    df = pd.DataFrame(rows, columns=['dia', 'hora', 'escenario'] + VARIABLES)
    # Anomalías intencionadas: no representan incidencias observadas en sensores.
    df.loc[[5, 980], 'p_total_kw'] = np.nan
    bruto = pd.concat([df, df.iloc[[100]]], ignore_index=True)
    rng_eventos = np.random.default_rng(config['semilla'] + 1)
    eventos = pd.DataFrame({
        'dia': np.arange(1, config['dias'] + 1),
        'inspecciones': config['inspecciones_dia'],
        'rechazos': rng_eventos.binomial(config['inspecciones_dia'], config['prob_rechazo'], config['dias']),
        'avisos': rng_eventos.poisson(config['avisos_dia'], config['dias'])})
    return bruto, eventos


def limpiar_datos(bruto):
    """Recibe una tabla bruta; valida, elimina duplicados exactos y reconstruye
    totales ausentes por balance; devuelve tabla limpia e informe de calidad.
    No descarta valores por ser extremos ni rellena mediciones desconocidas.
    """
    df = bruto.copy()
    informe = {'filas_brutas': len(df), 'duplicados_exactos': int(df.duplicated().sum())}
    df = df.drop_duplicates().copy()
    if df.duplicated(['dia', 'hora', 'escenario']).any():
        raise ValueError('Hay registros incompatibles para una misma clave.')
    falta = df['p_total_kw'].isna()
    informe['totales_reconstruidos'] = int(falta.sum())
    df.loc[falta, 'p_total_kw'] = df.loc[falta, ['p_it_kw', 'p_refrigeracion_kw', 'p_otros_kw']].sum(axis=1, min_count=3)
    if df.isna().any().any() or not np.isfinite(df[VARIABLES].to_numpy()).all():
        raise ValueError('Quedan valores ausentes o no finitos.')
    if not df.escenario.isin(['base', 'mejorado']).all():
        raise ValueError('Escenario no reconocido.')
    if (df[['p_it_kw', 'p_refrigeracion_kw', 'p_otros_kw']] <= 0).any().any():
        raise ValueError('Potencia no positiva.')
    if not df.hora.between(0, 23).all() or not df.dia.between(1, CONFIG['dias']).all():
        raise ValueError('Día u hora fuera de rango.')
    balance = df.p_it_kw + df.p_refrigeracion_kw + df.p_otros_kw
    if not np.allclose(df.p_total_kw, balance, atol=1e-9):
        raise ValueError('No se cumple el balance de potencia.')
    if not np.allclose(df.pue_horario, df.p_total_kw / df.p_it_kw, atol=1e-9):
        raise ValueError('PUE incoherente con las potencias.')
    if len(df) != 2 * CONFIG['dias'] * CONFIG['horas']:
        raise ValueError('Número de registros inesperado.')
    por_dia = df.groupby(['dia', 'escenario']).size()
    if not por_dia.eq(24).all():
        raise ValueError('Días incompletos.')
    df = df.sort_values(['dia', 'hora', 'escenario']).reset_index(drop=True)
    informe.update(filas_limpias=len(df), ausentes_finales=int(df.isna().sum().sum()))
    return df, informe


def agregar_por_dia(df):
    """Recibe horas con Δt=1 h; devuelve energías diarias y PUE por cociente
    de sumas. Una suma de potencias por una hora equivale a energía en kWh.
    """
    diario = df.groupby(['dia', 'escenario'], as_index=False).agg(
        e_it_kwh=('p_it_kw', 'sum'), e_total_kwh=('p_total_kw', 'sum'),
        e_refrigeracion_kwh=('p_refrigeracion_kw', 'sum'),
        temperatura_exterior_media_c=('temperatura_exterior_c', 'mean'))
    diario['p_it_media_kw'] = diario.e_it_kwh / 24
    diario['pue_diario'] = diario.e_total_kwh / diario.e_it_kwh
    return diario


def resumen_descriptivo(df, variables, grupo='escenario'):
    """Recibe tabla, variables y grupo; devuelve medidas con s y varianza
    muestrales (n−1). La moda exacta se omite para variables continuas.
    """
    rows = []
    for nombre, tabla in df.groupby(grupo):
        for var in variables:
            x = tabla[var]
            rows.append(dict(grupo=nombre, variable=var, n=len(x), media=x.mean(),
                             mediana=x.median(), s=x.std(ddof=1), varianza=x.var(ddof=1),
                             cv_pct=100*x.std(ddof=1)/x.mean(), minimo=x.min(),
                             q1=x.quantile(.25), q3=x.quantile(.75),
                             p95=x.quantile(.95), maximo=x.max(), rango=x.max()-x.min()))
    return pd.DataFrame(rows)


def analizar_relacion(diario):
    """Recibe datos diarios; calcula covarianza y Pearson en el escenario base
    entre ambiente y energía de refrigeración. Devuelve valores descriptivos;
    la asociación está parcialmente impuesta por la simulación.
    """
    b = diario[diario.escenario.eq('base')]
    x, y = b.temperatura_exterior_media_c, b.e_refrigeracion_kwh
    return dict(n=len(b), covarianza=float(np.cov(x, y, ddof=1)[0, 1]),
                pearson_r=float(stats.pearsonr(x, y).statistic),
                spearman_rho=float(stats.spearmanr(x, y).statistic))


def probabilidades(eventos, diario):
    """Recibe recuentos y medias diarias; estima p, λ, μ y s y devuelve
    probabilidades Binomial, Poisson y Normal, además de cálculos manuales.
    Son modelos exploratorios con parámetros estimados de datos sintéticos.
    """
    n = CONFIG['inspecciones_dia']
    phat = eventos.rechazos.sum() / eventos.inspecciones.sum()
    lam = eventos.avisos.mean()
    it = diario[diario.escenario.eq('base')].p_it_media_kw
    mu, s = it.mean(), it.std(ddof=1)
    return dict(n_binomial=n, inspecciones_totales=int(eventos.inspecciones.sum()),
                rechazos_totales=int(eventos.rechazos.sum()), p_estimado=float(phat),
                binomial_al_menos_uno=float(stats.binom.sf(0, n, phat)),
                binomial_manual=float(1-(1-phat)**n),
                lambda_estimada=float(lam), avisos_totales=int(eventos.avisos.sum()),
                poisson_al_menos_tres=float(stats.poisson.sf(2, lam)),
                poisson_manual=float(1-math.exp(-lam)*(1+lam+lam**2/2)),
                mu_it_kw=float(mu), s_it_kw=float(s),
                z_130=float((130-mu)/s), normal_mayor_130=float(stats.norm.sf(130, mu, s)),
                normal_manual=float(.5*math.erfc((130-mu)/(s*math.sqrt(2)))),
                fraccion_empirica_mayor_130=float((it>130).mean()),
                shapiro_it_p=float(stats.shapiro(it).pvalue),
                moda_avisos=[int(x) for x in eventos.avisos.mode()],
                frecuencia_moda_avisos=int(eventos.avisos.value_counts().max()))


def contraste_pareado(diario):
    """Recibe datos diarios; empareja escenarios por día, contrasta ahorro
    medio >0 con t pareada, devuelve t, p e IC bilateral 95 % del ahorro.
    """
    pares = diario.pivot(index='dia', columns='escenario', values='e_total_kwh')
    if pares.isna().any().any():
        raise ValueError('Hay pares incompletos.')
    d = pares['base'] - pares['mejorado']
    n = len(d); sd = d.std(ddof=1); se = sd/np.sqrt(n)
    t = d.mean()/se
    test = stats.ttest_rel(pares['base'], pares['mejorado'], alternative='greater')
    margen = stats.t.ppf(.975, n-1)*se
    return dict(n=n, gl=n-1, alpha=CONFIG['alpha'], ahorro_medio_kwh=float(d.mean()),
                s_ahorro_kwh=float(sd), error_estandar_kwh=float(se), t_manual=float(t),
                t_scipy=float(test.statistic), p_unilateral=float(test.pvalue),
                ic95_inferior=float(d.mean()-margen), ic95_superior=float(d.mean()+margen),
                shapiro_diferencias_p=float(stats.shapiro(d).pvalue),
                ahorro_pct=float(100*d.sum()/pares['base'].sum()),
                anualizacion_ilustrativa_kwh=float(d.mean()*365))


def comprobar_resultados(df, diario, pr, contraste):
    """Recibe datos y resultados; comprueba balances, emparejamiento y
    cálculos independientes. Devuelve un informe; ante fallos detiene el análisis.
    """
    pares = df.pivot(index=['dia','hora'], columns='escenario', values='p_it_kw')
    assert np.allclose(pares.base, pares.mejorado), 'La carga IT no está emparejada'
    assert np.isclose(df.p_total_kw.sum(), diario.e_total_kwh.sum()), 'Balance horario/diario'
    assert np.isclose(pr['binomial_al_menos_uno'], pr['binomial_manual']), 'Binomial'
    assert np.isclose(pr['poisson_al_menos_tres'], pr['poisson_manual']), 'Poisson'
    assert np.isclose(pr['normal_mayor_130'], pr['normal_manual']), 'Normal'
    assert np.isclose(contraste['t_manual'], contraste['t_scipy']), 'Estadístico t'
    # Validación dimensional y aritmética de los resultados centrales de Fase I.
    assert 120*1.6*24*365 == 1681920
    assert np.isclose(120*(1.6-1.4)*24*365, 210240)
    assert np.isclose(120*1.02**11, 149.2049170073583)
    assert np.isclose(-np.log(.25)/.25, 5.545177444479562)
    return dict(estado='CORRECTO', controles=['Carga IT idéntica entre escenarios',
        'Balance de energía horario-diario', 'Binomial: fórmula vs SciPy',
        'Poisson: fórmula vs SciPy', 'Normal: erfc vs SciPy',
        't: cálculo directo vs SciPy', 'Cálculos centrales de Fase I'])


def crear_figuras(df, diario, eventos, destino):
    """Recibe tablas y carpeta; guarda figuras PNG y devuelve sus rutas.
    Los gráficos describen datos simulados y no validan una instalación real.
    """
    destino=Path(destino); destino.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False,
                         'axes.spines.right': False, 'figure.dpi': 120})
    paths=[]; colors=['#245c81','#d37a2d']
    def guardar(fig, nombre):
        fig.tight_layout(); ruta=destino/nombre
        fig.savefig(ruta, dpi=190, bbox_inches='tight'); plt.close(fig);paths.append(str(ruta))
    # Fase I: se regeneran a partir de sus modelos y sin redondeo intermedio.
    meses=np.arange(1,13)
    fig,ax=plt.subplots(figsize=(7.4,3.6))
    ax.plot(meses,(240+10*(meses-1))*.5,'o-',label='Ampliación: 10 servidores/mes',color=colors[1])
    ax.plot(meses,120*1.02**(meses-1),'o-',label='Carga: +2 %/mes',color=colors[0])
    ax.set(xlabel='Mes (primer mes = 1)',ylabel='Potencia IT (kW)',title='Dos escenarios hipotéticos de crecimiento');ax.legend();ax.grid(alpha=.2)
    guardar(fig,'01_crecimiento_fase_I.png')
    t=np.linspace(0,24,241)
    fig,ax=plt.subplots(figsize=(7.4,3.4));ax.plot(t,35+8*np.cos(2*np.pi*(t-15)/24),color=colors[0])
    ax.set(xlabel='Hora del día (h)',ylabel='Potencia de refrigeración (kW)',title='Ciclo diario ilustrativo de refrigeración');ax.grid(alpha=.2)
    guardar(fig,'02_refrigeracion_fase_I.png')
    fig,ax=plt.subplots(figsize=(7.4,3.4))
    for esc,col in zip(['base','mejorado'],colors):
        d=diario[diario.escenario.eq(esc)];ax.plot(d.dia,d.e_total_kwh,'o-',ms=3,label=esc.capitalize(),color=col)
    ax.set(xlabel='Par de condiciones simuladas (día)',ylabel='Energía total diaria (kWh)',title='Misma carga IT y ambiente en cada par');ax.legend();ax.grid(alpha=.2)
    guardar(fig,'03_lineas_energia_diaria.png')
    fig,ax=plt.subplots(figsize=(7.4,3.4))
    medias=diario.groupby('escenario').e_total_kwh.mean().reindex(['base','mejorado'])
    ax.bar(['Base','Mejorado'],medias,color=colors,width=.55)
    for i,v in enumerate(medias):ax.text(i,v+45,f'{v:,.1f} kWh',ha='center')
    ax.set(ylim=(0,max(medias)*1.18),ylabel='Energía total media diaria (kWh)',title='Comparación de 30 pares de días simulados')
    guardar(fig,'04_barras_energia_media.png')
    b=diario[diario.escenario.eq('base')]
    fig,ax=plt.subplots(figsize=(7.4,3.4));ax.hist(b.p_it_media_kw,bins=7,edgecolor='white',color=colors[0])
    ax.axvline(130,color=colors[1],ls='--',label='Umbral ilustrativo: 130 kW')
    ax.set(xlabel='Potencia IT media diaria (kW)',ylabel='Número de días',title='Distribución de 30 medias diarias de carga IT');ax.legend()
    guardar(fig,'05_histograma_carga_it.png')
    fig,ax=plt.subplots(figsize=(7.4,3.4));ax.scatter(b.temperatura_exterior_media_c,b.e_refrigeracion_kwh,color=colors[0])
    ax.set(xlabel='Temperatura exterior media diaria (°C)',ylabel='Energía diaria de refrigeración (kWh)',title='Asociación en el escenario base simulado');ax.grid(alpha=.2)
    guardar(fig,'06_dispersion_temperatura.png')
    tabla=df[df.escenario.eq('base')].pivot(index='dia',columns='hora',values='p_total_kw')
    fig,ax=plt.subplots(figsize=(7.4,4.0));im=ax.imshow(tabla,aspect='auto',origin='lower',cmap='viridis')
    ax.set(xticks=np.arange(0,24,3),yticks=[0,9,19,29],yticklabels=[1,10,20,30],xlabel='Hora del día (h)',ylabel='Día simulado',title='Mapa de calor de la potencia total: escenario base')
    fig.colorbar(im,ax=ax,label='Potencia total (kW)');guardar(fig,'07_mapa_calor.png')
    diferencias=diario.pivot(index='dia',columns='escenario',values='e_total_kwh').eval('base-mejorado')
    fig,axs=plt.subplots(1,2,figsize=(7.4,3.1))
    stats.probplot(b.p_it_media_kw,dist='norm',plot=axs[0]);axs[0].set(title='Carga IT diaria',xlabel='Cuantiles normales teóricos',ylabel='Potencia IT (kW)')
    stats.probplot(diferencias,dist='norm',plot=axs[1]);axs[1].set(title='Ahorros diarios pareados',xlabel='Cuantiles normales teóricos',ylabel='Ahorro (kWh)')
    guardar(fig,'08_diagnostico_normalidad.png')
    return paths


def ejecutar(raiz=ROOT):
    """Orquesta generación, carga, limpieza, análisis, comprobación y exportación."""
    raiz=Path(raiz)
    for sub in ['datos','resultados','figuras']:(raiz/sub).mkdir(parents=True,exist_ok=True)
    bruto,eventos=generar_datos()
    bruto.to_csv(raiz/'datos/horario_bruto.csv',index=False)
    eventos.to_csv(raiz/'datos/eventos_diarios.csv',index=False)
    # Lectura del CSV: la misma ruta que utiliza el notebook para el análisis.
    bruto=pd.read_csv(raiz/'datos/horario_bruto.csv')
    eventos=pd.read_csv(raiz/'datos/eventos_diarios.csv')
    limpio,calidad=limpiar_datos(bruto);diario=agregar_por_dia(limpio)
    limpio.to_csv(raiz/'datos/horario_limpio.csv',index=False)
    diario.to_csv(raiz/'resultados/resumen_diario.csv',index=False)
    dh=resumen_descriptivo(limpio,VARIABLES)
    dd=resumen_descriptivo(diario,['e_total_kwh','p_it_media_kw','pue_diario'])
    dh.to_csv(raiz/'resultados/descriptiva_horaria.csv',index=False)
    dd.to_csv(raiz/'resultados/descriptiva_diaria.csv',index=False)
    relacion=analizar_relacion(diario);pr=probabilidades(eventos,diario);test=contraste_pareado(diario)
    verificaciones=comprobar_resultados(limpio,diario,pr,test)
    puetotal={esc:float(g.e_total_kwh.sum()/g.e_it_kwh.sum()) for esc,g in diario.groupby('escenario')}
    resultados=dict(config=CONFIG,calidad=calidad,relacion=relacion,probabilidades=pr,
                    contraste=test,pue_periodo=puetotal,verificaciones=verificaciones,
                    entorno=dict(python=platform.python_version(),numpy=np.__version__,
                                 pandas=pd.__version__,scipy=scipy.__version__,matplotlib=matplotlib.__version__))
    (raiz/'resultados/resultados.json').write_text(json.dumps(resultados,indent=2,ensure_ascii=False),encoding='utf-8')
    (raiz/'datos/configuracion.json').write_text(json.dumps(CONFIG,indent=2),encoding='utf-8')
    crear_figuras(limpio,diario,eventos,raiz/'figuras')
    return resultados

if __name__=='__main__':
    r=ejecutar()
    print(json.dumps(r,indent=2,ensure_ascii=False))
