import streamlit as st
import pandas as pd
from datetime import datetime
import numpy as np
from pathlib import Path

# --- Listas de KPIs para a ENTRADA de dados ---
KPIS_CANS_INPUT = [
    'Gas (m³/000) / (kg/000)', 'Ink Usage (kg/000)', 'Inside Spray Usage(kg/000)', 'Metal Can (kg/000)','Scrap (kg/000)', 'Spoilage(%)',
    'Variable Light (kwh/000)- Fora Ponta',
    'Variable Light (kwh/000)- Ponta',
    'Varnish Usage (kg/000)',
    'Water & Sewer (m³/000)'
]

KPIS_ENDS_INPUT = [
    'Metal End (kg/000)','Spoilage (%)','Tab Scrap (kg/000)','Compound Usage (kg/000)',
    'Variable Light (kwh/000)- Fora Ponta',
    'Variable Light (kwh/000)- Ponta',
    'Water & Sewer (m³/000)',
    'Metal Tab (kg/000)','End Scrap (kg/000)'
]

# --- Listas de KPIs para a ORDEM da exibição final ---
KPIS_CANS = [
    'Gas (m³/000) / (kg/000)', 'Ink Usage (kg/000)', 'Inside Spray Usage(kg/000)', 'Metal Can (kg/000)','Scrap (kg/000)', 'Spoilage(%)',
    'Variable Light (kwh/000)', 'Varnish Usage (kg/000)',
    'Water & Sewer (m³/000)'
]

KPIS_ENDS = [
    'Metal End (kg/000)','Spoilage (%)','Tab Scrap (kg/000)','Compound Usage (kg/000)',
    'Variable Light (kwh/000)',
    'Water & Sewer (m³/000)',
    'Metal Tab (kg/000)','End Scrap (kg/000)'
]

# -------------------------------
# CONFIGURAÇÃO DE GÁS
# -------------------------------
GAS_FACTORS = {
    'GLP': 12.78,
    'GN': 10.76
}
PLANTAS_GAS_TIPO = {
    'BRAC': 'GLP',
    'BRFR': 'GLP',
    'PYAS': 'GLP',
}
GAS_KPI_NAME = 'Gas (m³/000) / (kg/000)'
# -------------------------------

PLANTAS_CONFIG = {}
# Plantas de latas
for planta in ['ARBA', 'BRBR', 'BR3R', 'BRJC', 'BRPA', 'BRET', 'BRPE', 'BRFR', 'BRAC', 'PYAS', 'CLSA']:
    PLANTAS_CONFIG[planta] = {'tipo': 'Cans', 'kpis': KPIS_CANS_INPUT}
# Plantas de tampas
for planta in ['BRAM', 'PYAST', 'BRPET', 'BR3RT']:
    PLANTAS_CONFIG[planta] = {'tipo': 'Ends', 'kpis': KPIS_ENDS_INPUT}

# MESES abreviados
MESES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
         'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']


def agregar_energia(df: pd.DataFrame, final_kpi_order: list) -> pd.DataFrame:
    """
    Soma os KPIs de energia 'Ponta' e 'Fora Ponta' em um único KPI
    e reordena o DataFrame para a exibição final.
    """
    df = df.copy()
    kpi_ponta = 'Variable Light (kwh/000)- Ponta'
    kpi_fora_ponta = 'Variable Light (kwh/000)- Fora Ponta'
    kpi_unificado = 'Variable Light (kwh/000)'

    if kpi_ponta in df.index and kpi_fora_ponta in df.index:
        soma_energia = df.loc[kpi_ponta] + df.loc[kpi_fora_ponta]
        df.loc[kpi_unificado] = soma_energia
        df = df.drop(index=[kpi_ponta, kpi_fora_ponta])

    elif kpi_ponta in df.columns and kpi_fora_ponta in df.columns:
        soma_energia = df[kpi_ponta] + df[kpi_fora_ponta]
        df[kpi_unificado] = soma_energia
        df = df.drop(columns=[kpi_ponta, kpi_fora_ponta])

    if set(df.index).issuperset(set(final_kpi_order)):
        return df.reindex(index=final_kpi_order).dropna(how='all')
    elif set(df.columns).issuperset(set(final_kpi_order)):
        return df.reindex(columns=final_kpi_order).dropna(how='all')

    return df

def validar_dados(vol_df, aop_df):
    erros = []
    if (vol_df < 0).any().any():
        erros.append("Volume de produção não pode ser negativo")
    if pd.isna(aop_df['FY']).any():
        erros.append("Há FY não informado (NaN). Preencha com 0 quando não houver meta.")
    return erros

def get_plant_store(planta: str):
    store = st.session_state.setdefault('plant_store', {})
    if planta not in store:
        store[planta] = {
            'num_formatos': 2,
            'nomes_formatos': [f'Formato_{i+1}' for i in range(2)],
            'dados': {}
        }
    return store[planta]

def set_plant_store(planta: str, plant_state: dict):
    st.session_state.setdefault('plant_store', {})
    st.session_state['plant_store'][planta] = plant_state

def _to_float_br(x):
    if isinstance(x, str):
        s = x.strip().replace(" ", "")
        if ',' in s:
            s = s.replace('.', '').replace(',', '.')
        try:
            return float(s)
        except Exception:
            return x
    return x

def corrige_decimais_df(df: pd.DataFrame) -> pd.DataFrame:
    return df.applymap(_to_float_br)

def main():
    st.set_page_config(
        page_title="Calculadora de Reforecast",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    COR_PRIMARIA = "#1140FE"
    COR_SECUNDARIA = "#0029B3"
    COR_FUNDO = "#FFFFFF"
    COR_FUNDO_SECUNDARIO = "#F8F9FB"
    COR_BORDA_CARD = "#E6EAF1"
    COR_TEXTO = "#333333"
    COR_YTD_BG = "#E8EDFF"
    COR_CHIP_YTD = "#1140FE"
    COR_CHIP_FUT = "#B0B7C9"
    COR_TAB_ATIVA_BG = COR_PRIMARIA
    COR_TAB_ATIVA_TX = "#FFFFFF"
    COR_TAB_INATIVA_BG = "#EEF2FF"
    COR_TAB_INATIVA_TX = "#3B3B3B"
    COR_TAB_BORDA = "#D6DAE3"
    COR_TAB_HOVER_BG = "#E8EDFF"

    BASE_DIR = Path(__file__).parent
    # Define o caminho para os dois logos
    LOGO_URL = BASE_DIR / "logo.png"
    LOGO_BRANCO_URL = BASE_DIR / "logo_branco.png"

    # Bloco de CSS Universal e Automático
    st.markdown(f"""
    <style>
        /* Define variáveis de cores para o tema claro (padrão) */
        :root {{
            --cor-primaria: {COR_PRIMARIA};
            --cor-secundaria: {COR_SECUNDARIA};
            --cor-fundo: {COR_FUNDO};
            --cor-fundo-secundario: {COR_FUNDO_SECUNDARIO};
            --cor-borda-card: {COR_BORDA_CARD};
            --cor-texto: {COR_TEXTO};
            --cor-tab-ativa-bg: {COR_TAB_ATIVA_BG};
            --cor-tab-ativa-tx: {COR_TAB_ATIVA_TX};
            --cor-tab-inativa-bg: {COR_TAB_INATIVA_BG};
            --cor-tab-inativa-tx: {COR_TAB_INATIVA_TX};
            --cor-tab-borda: {COR_TAB_BORDA};
            --cor-tab-hover-bg: {COR_TAB_HOVER_BG};
        }}

        .stApp {{
            background-color: var(--cor-fundo);
            color: var(--cor-texto);
        }}
        h1, h2, h3, h4 {{ color: var(--cor-primaria); }}
        [data-testid="stSidebar"] {{ background-color: var(--cor-fundo-secundario); }}
        
        /* Classes para controlar a visibilidade dos logos */
        .logo-light {{ display: block; }}
        .logo-dark {{ display: none; }}

        .stButton>button {{
            border: none; background-color: var(--cor-primaria); color: white;
            border-radius: 8px; padding: 10px 20px; font-weight: 600; transition: .3s;
        }}
        .stButton>button:hover {{ background-color: var(--cor-secundaria); transform: scale(1.02); }}
        .st-emotion-cache-1r6slb0 {{
            border: 1px solid var(--cor-borda-card);
            border-radius: 12px; padding: 1rem;
            background-color: var(--cor-fundo-secundario);
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }}
        .stTabs [data-baseweb="tab-list"] {{ gap: 6px; }}
        .stTabs [data-baseweb="tab-list"] button {{
            background-color: var(--cor-tab-inativa-bg); color: var(--cor-tab-inativa-tx);
            border: 1px solid var(--cor-tab-borda); border-bottom: none;
            padding: 8px 14px; border-radius: 10px 10px 0 0; box-shadow: none;
        }}
        .stTabs [data-baseweb="tab-list"] button:hover {{ background-color: var(--cor-tab-hover-bg); }}
        .stTabs [data-baseweb="tab-list"] button p {{ font-weight: 600; margin: 0; }}
        .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {{
            background-color: var(--cor-tab-ativa-bg); color: var(--cor-tab-ativa-tx); border-color: var(--cor-tab-ativa-bg);
        }}
        .stTabs [data-baseweb="tab-highlight"] {{ background-color: transparent !important; }}
        .stTabs [data-baseweb="tab-panel"] {{
            border: 1px solid var(--cor-tab-borda); border-top: 0;
            border-radius: 0 10px 10px 10px; padding: 1rem; background: var(--cor-fundo);
        }}
        .chips {{ display: flex; gap: .4rem; flex-wrap: wrap; }}
        .chip {{ padding: .14rem .5rem; border-radius: 999px; font-size: .80rem; font-weight: 600; }}
        .chip-ytd {{ background: {COR_CHIP_YTD}; color: white; }}
        .chip-fut {{ background: {COR_CHIP_FUT}; color: white; }}

        /* Regras que o navegador aplicará AUTOMATICAMENTE se o tema do usuário for escuro */
        @media (prefers-color-scheme: dark) {{
            :root {{
                --cor-primaria: #588BFF;
                --cor-secundaria: #84A9FF;
                --cor-fundo: #0E1117;
                --cor-fundo-secundario: #161B22;
                --cor-borda-card: #30363D;
                --cor-texto: #EAEAEA;
                --cor-tab-ativa-bg: #588BFF;
                --cor-tab-ativa-tx: #FFFFFF;
                --cor-tab-inativa-bg: #161B22;
                --cor-tab-inativa-tx: #EAEAEA;
                --cor-tab-borda: #30363D;
                --cor-tab-hover-bg: #21262D;
            }}
            
            /* Inverter a visibilidade dos logos no tema escuro */
            .logo-light {{ display: none; }}
            .logo-dark {{ display: block; }}

            [data-testid="stMetricLabel"], [data-testid="stMetricValue"] {{
                color: var(--cor-texto) !important;
            }}
            [data-testid="stAlert"] {{
                background-color: #2F3136 !important;
                color: #EAEAEA !important;
                border: 1px solid #4F545C !important;
            }}
            [data-testid="stAlert"] svg {{ fill: #EAEAEA !important; }}
        }}
    </style>
    """, unsafe_allow_html=True)

    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        try:
            # Exibir os dois logos, cada um em sua "caixa" (div) controlada pelo CSS
            st.markdown('<div class="logo-light">', unsafe_allow_html=True)
            st.image(str(LOGO_URL), width=150)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="logo-dark">', unsafe_allow_html=True)
            st.image(str(LOGO_BRANCO_URL), width=150)
            st.markdown('</div>', unsafe_allow_html=True)
        except Exception:
            pass
            
    with col_title:
        st.title("Calculadora de Reforecast")
        st.subheader("Readequação ao AOP")

    st.markdown("---")

    st.header("1️⃣ Seleção da Planta")
    with st.container(border=True):
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            lista_plantas = sorted(list(PLANTAS_CONFIG.keys()))
            planta_selecionada = st.selectbox(
                "Escolha a planta", options=[""] + lista_plantas,
                format_func=lambda x: "Selecione..." if x == "" else x,
                key="planta_select"
            )
        if not planta_selecionada:
            st.info("👆 Selecione uma planta para continuar")
            st.stop()
        with col2:
            tipo_planta = PLANTAS_CONFIG[planta_selecionada]['tipo']
            st.metric("Tipo de Planta", tipo_planta)

        with col3:
            fator_gas = 1.0
            tem_kpi_gas = any(GAS_KPI_NAME in kpi for kpi in PLANTAS_CONFIG[planta_selecionada]['kpis'])
            if tem_kpi_gas:
                tipo_gas = PLANTAS_GAS_TIPO.get(planta_selecionada, 'GN')
                fator_gas = GAS_FACTORS[tipo_gas]
                st.metric("Tipo de Gás", tipo_gas, help=f"Fator de conversão: {fator_gas}")

    kpis_da_planta = PLANTAS_CONFIG[planta_selecionada]['kpis']
    plant_state = get_plant_store(planta_selecionada)

    st.header("2️⃣ Configurações do Cálculo")
    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            mes_default = plant_state.get('mes_reforecast', 'Jun')
            mes_reforecast = st.select_slider(
                "Mês do Reforecast", options=MESES, value=mes_default,
                help="Mês final do período YTD",
                key=f"{planta_selecionada}_mes_reforecast"
            )
            plant_state['mes_reforecast'] = mes_reforecast
            set_plant_store(planta_selecionada, plant_state)

        idx_mes_reforecast = MESES.index(mes_reforecast)
        colunas_ytd = MESES[:idx_mes_reforecast + 1]
        colunas_futuro = MESES[idx_mes_reforecast + 1:]
        with col2:
            st.metric("Meses YTD", len(colunas_ytd))
        with col3:
            st.metric("Meses Futuros", len(colunas_futuro))

    def chips_meses(ytd_cols, fut_cols, titulo="Meses (YTD | Futuro)"):
        chips = "".join([f"<span class='chip chip-ytd'>{m}</span>" for m in ytd_cols] +
                        [f"<span class='chip chip-fut'>{m}</span>" for m in fut_cols])
        st.markdown(f"**{titulo}** \n<div class='chips'>{chips}</div>", unsafe_allow_html=True)

    st.header("3️⃣ Configuração de Formatos")
    with st.container(border=True):
        num_formatos = st.number_input(
            "Número de formatos", min_value=1, max_value=10,
            value=int(plant_state['num_formatos']),
            key=f"{planta_selecionada}_num_formatos"
        )
        plant_state['num_formatos'] = int(num_formatos)
        cols_nomes = st.columns(min(num_formatos, 4))
        nomes_guardados = plant_state.get('nomes_formatos', [])
        novos_nomes = []
        for i in range(num_formatos):
            default_nome = nomes_guardados[i] if i < len(nomes_guardados) else f"Formato_{i+1}"
            with cols_nomes[i % len(cols_nomes)]:
                nome_i = st.text_input(f"Formato {i+1}", value=default_nome, key=f"{planta_selecionada}_formato_nome_{i}")
            novos_nomes.append(nome_i)
        plant_state['nomes_formatos'] = novos_nomes
        set_plant_store(planta_selecionada, plant_state)

    st.markdown("---")

    st.header("4️⃣ Dados de Entrada por Formato")
    dados_formatos = {}
    tabs_formatos = st.tabs(plant_state['nomes_formatos'])

    for i, tab in enumerate(tabs_formatos):
        with tab:
            formato_atual = plant_state['nomes_formatos'][i]
            st.subheader(f"{formato_atual}")
            chips_meses(colunas_ytd, colunas_futuro)
            st.write("")
            dados_salvos = plant_state['dados'].get(i, {})

            st.markdown("##### 📈 Volume de Produção")
            df_volume_default = dados_salvos.get('volume', pd.DataFrame(0.0, index=["Volume Total"], columns=MESES))
            df_volume_editado = st.data_editor(df_volume_default, key=f"{planta_selecionada}_volume_{i}", use_container_width=True, num_rows="fixed")
            df_volume_editado = corrige_decimais_df(df_volume_editado).astype(float)

            st.markdown("##### 🎯 Coeficientes YTD + Ciclo Anterior")
            df_aop_default = dados_salvos.get('aop', pd.DataFrame(index=kpis_da_planta, columns=MESES + ['FY']).fillna(0.0))
            df_aop_editado = st.data_editor(df_aop_default, key=f"{planta_selecionada}_aop_{i}", use_container_width=True, num_rows="fixed", height=420)
            df_aop_editado = corrige_decimais_df(df_aop_editado).astype(float)

            st.markdown("##### 🧷 AOP ou Ciclo Anterior (Opcional)")
            df_aop_show_default = dados_salvos.get('aop_show', pd.DataFrame(index=kpis_da_planta, columns=MESES).fillna(0.0))
            df_aop_show_editado = st.data_editor(df_aop_show_default, key=f"{planta_selecionada}_aop_show_{i}", use_container_width=True, num_rows="fixed", height=420)
            df_aop_show_editado = corrige_decimais_df(df_aop_show_editado).astype(float)

            plant_state['dados'][i] = {'volume': df_volume_editado.fillna(0.0), 'aop': df_aop_editado.fillna(0.0), 'aop_show': df_aop_show_editado.fillna(0.0)}
            set_plant_store(planta_selecionada, plant_state)
            dados_formatos[formato_atual] = plant_state['dados'][i]

    st.markdown("---")

    def is_spoilage(kpi_name: str) -> bool:
        return 'spoilage' in kpi_name.lower()

    def calc_kpi_por_formato(formato: str, df_vol: pd.DataFrame, df_aop: pd.DataFrame):
        vol_mensal = df_vol.loc['Volume Total'].astype(float).reindex(MESES).fillna(0.0)
        resultados_coef_anual = {}
        metas_futuras = pd.DataFrame(0.0, index=df_aop.index, columns=MESES)
        bloqueados = set()

        for kpi in df_aop.index:
            serie = df_aop.loc[kpi].astype(float)
            serie_mes = serie.reindex(MESES).fillna(0.0)
            fy = float(serie.get('FY', 0.0))

            if is_spoilage(kpi):
                realizado_ytd = ((serie_mes[colunas_ytd] / 100.0) * vol_mensal[colunas_ytd]).sum()
                total_fy = (fy / 100.0) * vol_mensal.sum()
            else:
                realizado_ytd = (serie_mes[colunas_ytd] * vol_mensal[colunas_ytd]).sum()
                total_fy = fy * vol_mensal.sum()

            EPS = 1e-9
            if not np.isfinite(realizado_ytd):
                realizado_ytd = 0.0
            if not np.isfinite(total_fy):
                total_fy = 0.0

            cond_excedeu = (total_fy > 0) and ((realizado_ytd > total_fy) or np.isclose(realizado_ytd, total_fy, rtol=0.0, atol=EPS))
            if cond_excedeu:
                bloqueados.add(kpi)
                resultados_coef_anual[kpi] = 0.0
                metas_futuras.loc[kpi, :] = 0.0
                st.warning(f"🔔 O KPI **{kpi}** do formato **{formato}** ultrapassou seu limite de saldo líquido.")
                continue

            saldo_restante = max(total_fy - realizado_ytd, 0.0)
            vol_fut = vol_mensal[colunas_futuro].sum()

            if vol_fut <= 0.0 or saldo_restante <= 0.0:
                resultados_coef_anual[kpi] = 0.0
                metas_futuras.loc[kpi, colunas_futuro] = 0.0
                continue

            if is_spoilage(kpi):
                estimado_mes = (serie_mes[colunas_futuro] / 100.0) * vol_mensal[colunas_futuro]
            else:
                estimado_mes = (serie_mes[colunas_futuro]) * vol_mensal[colunas_futuro]

            total_estimado = float(estimado_mes.sum())
            if total_estimado <= 0.0:
                base_prop = vol_mensal[colunas_futuro]
                total_base = base_prop.sum()
                if total_base <= 0.0:
                    metas_coef = pd.Series(0.0, index=colunas_futuro)
                else:
                    proporcao = base_prop / total_base
                    metas_valor = proporcao * saldo_restante
                    if is_spoilage(kpi):
                        metas_coef = (metas_valor / vol_mensal[colunas_futuro]).replace([np.inf, -np.inf], 0.0).fillna(0.0) * 100.0
                    else:
                        metas_coef = (metas_valor / vol_mensal[colunas_futuro]).replace([np.inf, -np.inf], 0.0).fillna(0.0)
                metas_futuras.loc[kpi, colunas_futuro] = metas_coef.values
            else:
                proporcao = (estimado_mes / total_estimado).fillna(0.0)
                metas_valor = proporcao * saldo_restante
                if is_spoilage(kpi):
                    metas_coef = (metas_valor / vol_mensal[colunas_futuro]).replace([np.inf, -np.inf], 0.0).fillna(0.0) * 100.0
                else:
                    metas_coef = (metas_valor / vol_mensal[colunas_futuro]).replace([np.inf, -np.inf], 0.0).fillna(0.0)
                metas_futuras.loc[kpi, colunas_futuro] = metas_coef.values

            if is_spoilage(kpi):
                resultados_coef_anual[kpi] = (saldo_restante / vol_fut) * 100.0 if vol_fut > 0 else 0.0
            else:
                resultados_coef_anual[kpi] = saldo_restante / vol_fut if vol_fut > 0 else 0.0

        return {'bloqueado_por_kpi': bloqueados, 'coef_anual_necessario': pd.Series(resultados_coef_anual), 'metas_futuras': metas_futuras}

    def mult_gas_df(df: pd.DataFrame, fator: float) -> pd.DataFrame:
        if GAS_KPI_NAME in df.index and fator != 1.0:
            df = df.copy()
            df.loc[GAS_KPI_NAME] = df.loc[GAS_KPI_NAME] * fator
        return df

    def mult_gas_series_as_row(series: pd.Series, fator: float) -> pd.DataFrame:
        df = pd.DataFrame(series).T
        if GAS_KPI_NAME in df.columns and fator != 1.0:
            df = df.copy()
            df[GAS_KPI_NAME] = df[GAS_KPI_NAME] * fator
        return df

    st.header("5️⃣ Cálculo e Resultados")
    if st.button("🚀 Calcular Reforecast", type="primary", use_container_width=True, key=f"{planta_selecionada}_calc"):
        with st.spinner("Consolidando dados e executando cálculos..."):
            
            if PLANTAS_CONFIG[planta_selecionada]['tipo'] == 'Cans':
                final_kpi_order = KPIS_CANS
            else:
                final_kpi_order = KPIS_ENDS
            
            nomes_formatos = plant_state['nomes_formatos']
            volumes = {f: dados_formatos[f]['volume'] for f in nomes_formatos}
            aops = {f: dados_formatos[f]['aop'] for f in nomes_formatos}
            aops_show = {f: dados_formatos[f]['aop_show'] for f in nomes_formatos}

            resultados_por_formato = {}
            bloqueios_por_kpi = {k: set() for k in kpis_da_planta}
            for formato in nomes_formatos:
                res = calc_kpi_por_formato(formato, volumes[formato], aops[formato])
                resultados_por_formato[formato] = res
                for kpi in res['bloqueado_por_kpi']:
                    bloqueios_por_kpi[kpi].add(formato)

            kpis_bloqueados_no_geral = {k for k, fset in bloqueios_por_kpi.items() if len(fset) > 0}
            if len(kpis_bloqueados_no_geral) > 0:
                st.info("ℹ️ Para os KPIs com estouro em algum formato, o consolidado **Geral** foi suprimido para esses KPIs.")

            metas_finais_por_formato = {}
            avisos_por_formato = {}

            for formato in nomes_formatos:
                res = resultados_por_formato[formato]
                df_aop_formato = aops[formato]
                df_aop_show_formato = aops_show[formato]
                metas_a_exibir = res['metas_futuras'].copy()
                avisos_performance = []
                for kpi in kpis_da_planta:
                    coef_calculado = res['coef_anual_necessario'].get(kpi, 0.0)
                    coef_fy_meta = df_aop_formato.loc[kpi, 'FY']
                    if coef_fy_meta > 0 and coef_calculado > coef_fy_meta:
                        override_values = df_aop_show_formato.loc[kpi, colunas_futuro]
                        if override_values.sum() > 0:
                            avisos_performance.append(f"💡 KPI **{kpi}** teve performance melhor que o AOP. Exibindo valores de 'AOP ou Ciclo Anterior'.")
                            metas_a_exibir.loc[kpi, colunas_futuro] = override_values
                metas_finais_por_formato[formato] = metas_a_exibir
                avisos_por_formato[formato] = avisos_performance

            tab_labels = ['Geral'] + nomes_formatos
            abas = st.tabs(tab_labels)

            with abas[0]: # ABA GERAL
                st.subheader("Resultado Geral")
                if len(nomes_formatos) == 1:
                    formato_unico = nomes_formatos[0]
                    st.subheader(f"(Espelho de {formato_unico})")
                    chips_meses(colunas_ytd, colunas_futuro)
                    if avisos_por_formato[formato_unico]:
                        st.write("")
                        for aviso in avisos_por_formato[formato_unico]:
                            st.info(aviso)
                        st.write("")
                    res_unico = resultados_por_formato[formato_unico]
                    df_anual_row_fmt = mult_gas_series_as_row(res_unico['coef_anual_necessario'], fator_gas)
                    df_anual_row_fmt.index = ["Necessário (FY)"]
                    df_anual_agregado = agregar_energia(df_anual_row_fmt, final_kpi_order)
                    st.markdown(f"**📊 Valor Anual**")
                    st.dataframe(df_anual_agregado.style.format(formatter="{:.3f}"))
                    metas_finais = metas_finais_por_formato[formato_unico]
                    metas_fmt_out = mult_gas_df(metas_finais, fator_gas)
                    metas_agregadas = agregar_energia(metas_fmt_out, final_kpi_order)
                    st.markdown(f"**📅 Metas Mensais Futuras**")
                    st.dataframe(metas_agregadas.style.format(formatter="{:.3f}"))
                else: # Múltiplos formatos
                    chips_meses(colunas_ytd, colunas_futuro)
                    vol_total_df = pd.concat([volumes[f] for f in nomes_formatos]).groupby(level=0).sum()
                    realizado_ytd_total = pd.Series(0.0, index=kpis_da_planta)
                    total_fy_total = pd.Series(0.0, index=kpis_da_planta)
                    for kpi in kpis_da_planta:
                        for formato in nomes_formatos:
                            if formato in bloqueios_por_kpi.get(kpi, set()):
                                continue
                            vol_formato = volumes[formato].loc['Volume Total']
                            aop_formato = aops[formato].loc[kpi]
                            if is_spoilage(kpi):
                                realizado_ytd_total[kpi] += ((aop_formato[colunas_ytd] / 100.0) * vol_formato[colunas_ytd]).sum()
                                total_fy_total[kpi] += (aop_formato['FY'] / 100.0) * vol_formato.sum()
                            else:
                                realizado_ytd_total[kpi] += (aop_formato[colunas_ytd] * vol_formato[colunas_ytd]).sum()
                                total_fy_total[kpi] += aop_formato['FY'] * vol_formato.sum()
                    saldo_restante = (total_fy_total - realizado_ytd_total).clip(lower=0)
                    vol_fut_total = vol_total_df.loc['Volume Total', colunas_futuro].sum()
                    geral_coef_anual = pd.Series(0.0, index=kpis_da_planta)
                    if vol_fut_total > 0:
                        for kpi in kpis_da_planta:
                            if kpi in kpis_bloqueados_no_geral:
                                geral_coef_anual[kpi] = 0.0
                                continue
                            if is_spoilage(kpi):
                                geral_coef_anual[kpi] = (saldo_restante[kpi] / vol_fut_total) * 100.0
                            else:
                                geral_coef_anual[kpi] = saldo_restante[kpi] / vol_fut_total
                    df_anual_row_geral = mult_gas_series_as_row(geral_coef_anual, fator_gas)
                    df_anual_row_geral.index = ["Necessário (FY)"]
                    df_anual_geral_agregado = agregar_energia(df_anual_row_geral, final_kpi_order)
                    st.markdown("**📊 Valor Anual (Consolidado)**")
                    st.dataframe(df_anual_geral_agregado.style.format(formatter="{:.3f}"))
                    volumes_producao_futuros_total_por_mes = pd.Series(0.0, index=colunas_futuro)
                    for formato in nomes_formatos:
                        volumes_producao_futuros_total_por_mes += volumes[formato].loc['Volume Total', colunas_futuro]
                    geral_metas = pd.DataFrame(0.0, index=kpis_da_planta, columns=MESES)
                    with np.errstate(divide='ignore', invalid='ignore'):
                        for kpi in kpis_da_planta:
                            if kpi in kpis_bloqueados_no_geral:
                                geral_metas.loc[kpi, colunas_futuro] = 0.0
                                continue
                            soma_liquido_kpi_por_mes = pd.Series(0.0, index=colunas_futuro)
                            for formato in nomes_formatos:
                                if formato in bloqueios_por_kpi.get(kpi, set()):
                                    continue
                                metas_futuras_formato = resultados_por_formato[formato]['metas_futuras']
                                volume_futuro_formato = volumes[formato].loc['Volume Total', colunas_futuro]
                                coeficientes_futuros = metas_futuras_formato.loc[kpi, colunas_futuro]
                                if is_spoilage(kpi):
                                    valor_liquido_mensal = (coeficientes_futuros / 100.0) * volume_futuro_formato
                                else:
                                    valor_liquido_mensal = coeficientes_futuros * volume_futuro_formato
                                soma_liquido_kpi_por_mes += valor_liquido_mensal
                            coef_mensal = soma_liquido_kpi_por_mes / volumes_producao_futuros_total_por_mes
                            if is_spoilage(kpi):
                                geral_metas.loc[kpi, colunas_futuro] = coef_mensal.fillna(0.0) * 100.0
                            else:
                                geral_metas.loc[kpi, colunas_futuro] = coef_mensal.fillna(0.0)
                    geral_metas_out = mult_gas_df(geral_metas, fator_gas)
                    geral_metas_agregadas = agregar_energia(geral_metas_out, final_kpi_order)
                    st.markdown("**📅 Metas Mensais Futuras (Consolidado)**")
                    st.dataframe(geral_metas_agregadas.style.format(formatter="{:.3f}"))

            for pos, formato in enumerate(nomes_formatos, start=1):
                with abas[pos]:
                    st.subheader(f"Formato: {formato}")
                    chips_meses(colunas_ytd, colunas_futuro)
                    avisos = avisos_por_formato[formato]
                    if avisos:
                        st.write("")
                        for aviso in avisos:
                            st.info(aviso)
                        st.write("")
                    res_formato = resultados_por_formato[formato]
                    df_anual_row_fmt = mult_gas_series_as_row(res_formato['coef_anual_necessario'], fator_gas)
                    df_anual_row_fmt.index = ["Necessário (FY)"]
                    df_anual_formato_agregado = agregar_energia(df_anual_row_fmt, final_kpi_order)
                    st.markdown(f"**📊 Valor Anual ({formato})**")
                    st.dataframe(df_anual_formato_agregado.style.format(formatter="{:.3f}"))
                    metas_finais = metas_finais_por_formato[formato]
                    metas_fmt_out = mult_gas_df(metas_finais, fator_gas)
                    metas_formato_agregadas = agregar_energia(metas_fmt_out, final_kpi_order)
                    st.markdown(f"**📅 Metas Mensais Futuras ({formato})**")
                    st.dataframe(metas_formato_agregadas.style.format(formatter="{:.3f}"))

            st.success("✅ Cálculos concluídos com sucesso!")

    st.markdown("---")
    st.markdown(f"<div style='text-align: center; color: gray;'>Calculadora Reforecast v12.6 | {datetime.now().year}</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()