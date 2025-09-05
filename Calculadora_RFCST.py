import streamlit as st
import pandas as pd
from datetime import datetime
import numpy as np
from pathlib import Path


KPIS_CANS = [
    'Metal Can (kg/000)', 'Spoilage(%)', 'Scrap (kg/000)','Varnish Usage (kg/000)','Ink Usage (kg/000)',
    'Inside Spray Usage(kg/000)','Gas (m³/000) / (kg/000)', 'Thermal (kwh/000)','Consumo de Energia (kwh/000)',
    'Variable Light (kwh/000) - Fora Ponta', 'Variable Light (kwh/000) - Ponta','Water & Sewer (m³/000)'
]
KPIS_ENDS = [
    'Metal End (kg/000)','Spoilage (%)','Tab Scrap  (kg/000)','Compound Usage (kg/000)','Consumo de Energia (kwh/000)',
    'Variable Light (KwH) - Fora Ponta','Variable Light (KwH) - Ponta','Water & Sewer (m³/000)',
    'Metal Tab (kg/000)','End Scrap (kg/000)'
]

PLANTAS_CONFIG = {}
# Plantas de latas
for planta in ['ARBA', 'BRBR', 'BR3R', 'BRJC', 'BRPA', 'BRET', 'BRPE', 'BRFR', 'BRAC', 'PYAS', 'CLSA']:
    PLANTAS_CONFIG[planta] = {'tipo': 'Cans', 'kpis': KPIS_CANS}
# Plantas de tampas
for planta in ['BRAM', 'PYAST', 'BRPET', 'BR3RT']:
    PLANTAS_CONFIG[planta] = {'tipo': 'Ends', 'kpis': KPIS_ENDS}

# MESES abreviados
MESES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
         'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']


def validar_dados(vol_df, aop_df):
    erros = []
    if (vol_df < 0).any().any():
        erros.append("Volume de produção não pode ser negativo")
    if pd.isna(aop_df['FY']).any():
        erros.append("Há FY não informado (NaN). Preencha com 0 quando não houver meta.")
    return erros


def get_plant_store(planta: str):
    """Obtém (ou cria) o estado persistente da planta atual."""
    store = st.session_state.setdefault('plant_store', {})
    if planta not in store:
        store[planta] = {
            'num_formatos': 2,
            'nomes_formatos': [f'Formato_{i+1}' for i in range(2)],
            # dados por índice do formato: {i: {'volume': df, 'aop': df, 'aop_show': df}}
            'dados': {}
        }
    return store[planta]


def set_plant_store(planta: str, plant_state: dict):
    st.session_state.setdefault('plant_store', {})
    st.session_state['plant_store'][planta] = plant_state


# -------------------------------
# Helpers de locale BR para números
# -------------------------------
def _to_float_br(x):
    """
    Converte strings no padrão brasileiro para float.
    Exemplos:
      "12,25" -> 12.25
      "1.234,56" -> 1234.56
    Mantém valores não conversíveis como estão.
    """
    if isinstance(x, str):
        s = x.strip().replace(" ", "")
        # remove separador de milhar '.', troca decimal ',' por '.'
        if ',' in s:
            s = s.replace('.', '').replace(',', '.')
        # tenta converter
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

    # --- SIDEBAR (Avisos Importantes) ---
    with st.sidebar:
        st.markdown("## ⚠️ Avisos Importantes")
        st.markdown(
            "- **Quando a planta performa melhor que o AOP**: manteremos **os valores do AOP** para os meses futuros (ou seja, o AOP é preservado na exibição futura).\n"
            "- **Regra de bloqueio**: se o **Volume Líquido YTD** exceder o **Volume Líquido FY** (para um KPI/Formato), o cálculo daquele **formato/KPI** não é feito (permanece zero)."
        )
        st.markdown("---")
        #st.caption("Cole valores do Excel no formato brasileiro (ex.: `1.234,56`). O app converte automaticamente.")

    # --- VARIÁVEIS DE CORES E LOGO ---
    COR_PRIMARIA = "#1140FE"
    COR_SECUNDARIA = "#0029B3"
    COR_FUNDO = "#FFFFFF"
    COR_FUNDO_SECUNDARIO = "#F8F9FB"
    COR_BORDA_CARD = "#E6EAF1"
    COR_TEXTO = "#333333"
    COR_YTD_BG = "#E8EDFF"
    COR_CHIP_YTD = "#1140FE"
    COR_CHIP_FUT = "#B0B7C9"

    # Cores das abas
    COR_TAB_ATIVA_BG = COR_PRIMARIA
    COR_TAB_ATIVA_TX = "#FFFFFF"
    COR_TAB_INATIVA_BG = "#EEF2FF"
    COR_TAB_INATIVA_TX = "#3B3B3B"
    COR_TAB_BORDA = "#D6DAE3"
    COR_TAB_HOVER_BG = "#E8EDFF"

    BASE_DIR = Path(__file__).parent
    LOGO_URL = BASE_DIR / "logo.png"

    # --- CSS GLOBAL ---
    st.markdown(f"""
    <style>
        .stApp {{ background-color: {COR_FUNDO}; color: {COR_TEXTO}; }}
        h1, h2, h3, h4 {{ color: {COR_PRIMARIA}; }}
        [data-testid="stSidebar"] {{ background-color: {COR_FUNDO_SECUNDARIO}; }}

        .stButton>button {{
            border: none; background-color: {COR_PRIMARIA}; color: white;
            border-radius: 8px; padding: 10px 20px; font-weight: 600; transition: .3s;
        }}
        .stButton>button:hover {{ background-color: {COR_SECUNDARIA}; transform: scale(1.02); }}

        .st-emotion-cache-1r6slb0 {{
            border: 1px solid {COR_BORDA_CARD};
            border-radius: 12px;
            padding: 1rem;
            background-color: {COR_FUNDO_SECUNDARIO};
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }}

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {{ gap: 6px; }}
        .stTabs [data-baseweb="tab-list"] button {{
            background-color: {COR_TAB_INATIVA_BG};
            color: {COR_TAB_INATIVA_TX};
            border: 1px solid {COR_TAB_BORDA};
            border-bottom: none;
            padding: 8px 14px;
            border-radius: 10px 10px 0 0;
            box-shadow: none;
        }}
        .stTabs [data-baseweb="tab-list"] button:hover {{ background-color: {COR_TAB_HOVER_BG}; }}
        .stTabs [data-baseweb="tab-list"] button p {{ font-weight: 600; margin: 0; }}
        .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {{
            background-color: {COR_TAB_ATIVA_BG};
            color: {COR_TAB_ATIVA_TX};
            border-color: {COR_TAB_ATIVA_BG};
        }}
        .stTabs [data-baseweb="tab-highlight"] {{ background-color: transparent !important; }}
        .stTabs [data-baseweb="tab-panel"] {{
            border: 1px solid {COR_TAB_BORDA};
            border-top: 0;
            border-radius: 0 10px 10px 10px;
            padding: 1rem; background: {COR_FUNDO};
        }}

        /* Chips dos meses */
        .chips {{ display: flex; gap: .4rem; flex-wrap: wrap; }}
        .chip {{ padding: .14rem .5rem; border-radius: 999px; font-size: .80rem; font-weight: 600; }}
        .chip-ytd {{ background: {COR_CHIP_YTD}; color: white; }}
        .chip-fut {{ background: {COR_CHIP_FUT}; color: white; }}
        .chip-legend {{ opacity: .8; }}
    </style>
    """, unsafe_allow_html=True)

    # --- CABEÇALHO ---
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        try:
            st.image(str(LOGO_URL), width=150)
        except Exception:
            pass
    with col_title:
        st.title("Calculadora de Reforecast")
        st.subheader("Readequação ao AOP")

    st.markdown("---")

    # --- Passo 1: Seleção da Planta ---
    st.header("1️⃣ Seleção da Planta")
    with st.container(border=True):
        col1, col2 = st.columns([2, 1])
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
    kpis_da_planta = PLANTAS_CONFIG[planta_selecionada]['kpis']

    # Carrega/Cria estado da planta selecionada
    plant_state = get_plant_store(planta_selecionada)

    # --- Passo 2: Configurações do Cálculo ---
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

    # --- Util: chips visuais de meses ---
    def chips_meses(ytd_cols, fut_cols, titulo="Meses (YTD | Futuro)"):
        chips = "".join([f"<span class='chip chip-ytd'>{m}</span>" for m in ytd_cols] +
                        [f"<span class='chip chip-fut'>{m}</span>" for m in fut_cols])
        st.markdown(f"**{titulo}**  \n<div class='chips'>{chips}</div>", unsafe_allow_html=True)

    def titulo_coluna_mes(mes: str, ytd_cols):
        return f"{mes}"

    # --- Passo 3: Configuração de Formatos ---
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
                nome_i = st.text_input(
                    f"Formato {i+1}",
                    value=default_nome,
                    key=f"{planta_selecionada}_formato_nome_{i}"
                )
            novos_nomes.append(nome_i)
        plant_state['nomes_formatos'] = novos_nomes
        set_plant_store(planta_selecionada, plant_state)

    st.markdown("---")

    # --- Passo 4: Dados por Formato ---
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

            # Volume
            st.markdown("##### 📈 Volume de Produção")
            df_volume_default = dados_salvos.get('volume', pd.DataFrame(0.0, index=["Volume Total"], columns=MESES))
            cfg_vol = {m: st.column_config.NumberColumn(titulo_coluna_mes(m, colunas_ytd), format="%.0f")
                       for m in MESES}
            df_volume_editado = st.data_editor(
                df_volume_default, key=f"{planta_selecionada}_volume_{i}",
                use_container_width=True, num_rows="fixed",
                column_config=cfg_vol,
            )
            # CORRIGE VÍRGULA/PONTO
            df_volume_editado = corrige_decimais_df(df_volume_editado).astype(float)

            # AOP principal (contém FY)
            st.markdown("##### 🎯 Coeficientes YTD + Ciclo Anterior")
            df_aop_default = dados_salvos.get('aop', pd.DataFrame(index=kpis_da_planta, columns=MESES + ['FY']).fillna(0.0))
            for m in MESES:
                if m not in df_aop_default.columns:
                    df_aop_default[m] = 0.0
            if 'FY' not in df_aop_default.columns:
                df_aop_default['FY'] = 0.0
            cfg_aop = {m: st.column_config.NumberColumn(titulo_coluna_mes(m, colunas_ytd), format="%.3f")
                       for m in MESES}
            cfg_aop['FY'] = st.column_config.NumberColumn("🎯 FY", format="%.3f", required=False)
            df_aop_editado = st.data_editor(
                df_aop_default, column_config=cfg_aop, key=f"{planta_selecionada}_aop_{i}",
                use_container_width=True, num_rows="fixed",
                height=458 if PLANTAS_CONFIG[planta_selecionada]['tipo'] == 'Cans' else 388
            )
            # CORRIGE VÍRGULA/PONTO
            df_aop_editado = corrige_decimais_df(df_aop_editado).astype(float)

            # AOP (Exibição) — 12 meses (sem FY)
            st.markdown("##### 🧷 AOP ou Ciclo Anterior (Opcional)")
            df_aop_show_default = dados_salvos.get('aop_show', pd.DataFrame(index=kpis_da_planta, columns=MESES).fillna(0.0))
            for m in MESES:
                if m not in df_aop_show_default.columns:
                    df_aop_show_default[m] = 0.0
            cfg_show = {m: st.column_config.NumberColumn(titulo_coluna_mes(m, colunas_ytd), format="%.3f")
                        for m in MESES}
            df_aop_show_editado = st.data_editor(
                df_aop_show_default,
                column_config=cfg_show,
                key=f"{planta_selecionada}_aop_show_{i}",
                use_container_width=True,
                num_rows="fixed",
                height=458 if PLANTAS_CONFIG[planta_selecionada]['tipo'] == 'Cans' else 388
            )
            # CORRIGE VÍRGULA/PONTO
            df_aop_show_editado = corrige_decimais_df(df_aop_show_editado).astype(float)

            # Salva no estado
            plant_state['dados'][i] = {
                'volume': df_volume_editado.fillna(0.0),
                'aop': df_aop_editado.fillna(0.0),
                'aop_show': df_aop_show_editado.fillna(0.0)
            }
            set_plant_store(planta_selecionada, plant_state)

            dados_formatos[formato_atual] = plant_state['dados'][i]

    st.markdown("---")

    # --- Função de estilo (destaque YTD) ---
    def style_highlight_ytd(df: pd.DataFrame, ytd_cols):
        def _col_style(col):
            if col.name in ytd_cols:
                return ['background-color: ' + COR_YTD_BG] * len(col)
            return [''] * len(col)
        return df.style.apply(lambda c: _col_style(c), axis=0)

    # --- Helpers de cálculo por KPI ---
    def is_spoilage(kpi_name: str) -> bool:
        return 'spoilage' in kpi_name.lower()

    def _resultado_melhor_que_aop(metas_calc_row: pd.Series, aop_show_row: pd.Series, kpi_name: str) -> bool:
        """
        True se o resultado calculado para os meses FUTUROS for 'melhor' que o AOP.
        Assumimos 'menor é melhor' (Spoilage/consumos). Ajuste aqui se precisar.
        """
        meses = [m for m in colunas_futuro if m in metas_calc_row.index and m in aop_show_row.index]
        if not meses:
            return False
        return (metas_calc_row[meses].astype(float) <= aop_show_row[meses].astype(float)).all()

    def calc_kpi_por_formato(formato: str, df_vol: pd.DataFrame, df_aop: pd.DataFrame):
        """
        Retorna:
        - 'bloqueado_por_kpi': set(KPIs)
        - 'coef_anual_necessario': Series (index=KPI)
        - 'metas_futuras': DataFrame (index=KPI, columns=MESES)
        """
        vol_mensal = df_vol['Volume Total'].astype(float).reindex(MESES).fillna(0.0)
        resultados_coef_anual = {}
        metas_futuras = pd.DataFrame(0.0, index=df_aop.index, columns=MESES)

        bloqueados = set()

        for kpi in df_aop.index:
            serie = df_aop.loc[kpi].astype(float)
            serie_mes = serie.reindex(MESES).fillna(0.0)
            fy = float(serie.get('FY', 0.0))

            # YTD x FY
            if is_spoilage(kpi):
                realizado_ytd = ((serie_mes[colunas_ytd] / 100.0) * vol_mensal[colunas_ytd]).sum()
                total_fy = (fy / 100.0) * vol_mensal.sum()
            else:
                realizado_ytd = (serie_mes[colunas_ytd] * vol_mensal[colunas_ytd]).sum()
                total_fy = fy * vol_mensal.sum()

            if realizado_ytd > total_fy:
                bloqueados.add(kpi)
                resultados_coef_anual[kpi] = 0.0
                metas_futuras.loc[kpi, :] = 0.0
                continue

            saldo_restante = max(total_fy - realizado_ytd, 0.0)
            vol_fut = vol_mensal[colunas_futuro].sum()

            if vol_fut <= 0.0 or saldo_restante == 0.0:
                resultados_coef_anual[kpi] = 0.0
                metas_futuras.loc[kpi, :] = 0.0
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

            # coef anual necessário (FY)
            if is_spoilage(kpi):
                resultados_coef_anual[kpi] = (saldo_restante / max(vol_fut, 1e-9)) * 100.0
            else:
                resultados_coef_anual[kpi] = (saldo_restante / max(vol_fut, 1e-9))

        return {
            'bloqueado_por_kpi': bloqueados,
            'coef_anual_necessario': pd.Series(resultados_coef_anual).reindex(df_aop.index).fillna(0.0),
            'metas_futuras': metas_futuras.reindex(index=df_aop.index, columns=MESES).fillna(0.0)
        }

    # --- Passo 5: Cálculo e Resultados ---
    st.header("5️⃣ Cálculo e Resultados")
    if st.button("🚀 Calcular Reforecast", type="primary", use_container_width=True, key=f"{planta_selecionada}_calc"):

        with st.spinner("Consolidando dados e executando cálculos... Por favor, aguarde."):

            nomes_formatos = plant_state['nomes_formatos']

            # Monta dicionários por formato
            volumes = {}
            aops = {}
            aops_show = {}
            for i, formato in enumerate(nomes_formatos):
                df_vol = dados_formatos[formato]['volume'].T  # linhas = meses
                volumes[formato] = df_vol.reindex(index=MESES).fillna(0.0)

                df_aop = dados_formatos[formato]['aop'].copy()
                df_aop.index = pd.Index(df_aop.index, name='KPI')
                aops[formato] = df_aop.reindex(index=kpis_da_planta, columns=MESES + ['FY']).fillna(0.0)

                df_aop_show = dados_formatos[formato]['aop_show'].copy()
                df_aop_show.index = pd.Index(df_aop_show.index, name='KPI')
                aops_show[formato] = df_aop_show.reindex(index=kpis_da_planta, columns=MESES).fillna(0.0)

            # Cálculo por formato e por KPI
            resultados_por_formato = {}
            bloqueios_por_kpi = {k: set() for k in kpis_da_planta}
            for formato in nomes_formatos:
                res = calc_kpi_por_formato(formato, volumes[formato], aops[formato])
                resultados_por_formato[formato] = res
                for k in res['bloqueado_por_kpi']:
                    bloqueios_por_kpi[k].add(formato)

            # --- AVISOS E PREPARAÇÃO DE TABS ---
            # Tab order: Geral primeiro
            tab_labels = ['Geral'] + nomes_formatos
            abas = st.tabs(tab_labels)

            # Guardar logs de avisos
            aop_melhor_logs = []           # (formato, kpi) necessário > FY → AOP aplicado
            aop_mantido_melhor_logs = []   # (formato, kpi) mantido AOP pq resultado calculado ficou melhor que AOP

            # ---------- ABA GERAL (primeira) ----------
            with abas[0]:
                st.subheader("Consolidado Geral")
                chips_meses(colunas_ytd, colunas_futuro)

                # Caso tenha somente 1 formato: Geral = espelho do formato (incluindo AOP lógico)
                if len(nomes_formatos) == 1:
                    formato = nomes_formatos[0]
                    coef_anual_fmt = resultados_por_formato[formato]['coef_anual_necessario'].copy()
                    fy_series = aops[formato]['FY'].astype(float).reindex(kpis_da_planta).fillna(0.0)
                    metas_fmt = resultados_por_formato[formato]['metas_futuras'].copy()

                    # (NOVO) manter AOP quando resultado calculado é melhor que AOP
                    for kpi in kpis_da_planta:
                        if _resultado_melhor_que_aop(metas_fmt.loc[kpi], aops_show[formato].loc[kpi], kpi):
                            metas_fmt.loc[kpi, colunas_futuro] = aops_show[formato].loc[kpi, colunas_futuro].values
                            aop_mantido_melhor_logs.append((formato, kpi))

                    # AOP aplicado quando necessário > FY
                    substituir_por_aop = fy_series.index[(coef_anual_fmt.fillna(0.0) > fy_series.fillna(0.0))].tolist()
                    if len(colunas_futuro) > 0 and substituir_por_aop:
                        for kpi in substituir_por_aop:
                            metas_fmt.loc[kpi, colunas_futuro] = aops_show[formato].loc[kpi, colunas_futuro].values
                            aop_melhor_logs.append((formato, kpi))

                    # Exibição do valor anual (colunas = KPIs; uma linha) — formatação BR (Spoilage 2c, demais 3c)
                    coef_anual_display = coef_anual_fmt.copy()
                    for kpi in substituir_por_aop:
                        coef_anual_display.loc[kpi] = fy_series.loc[kpi]

                    def _fmt_val(kpi, v):
                        return f"{float(v):.2f}%" if is_spoilage(kpi) else f"{float(v):.3f}"
                    linha = {k: _fmt_val(k, coef_anual_display.get(k, 0.0)) for k in kpis_da_planta}
                    df_anual_row = pd.DataFrame([linha], index=["Necessário (FY)"])

                    st.markdown("**📊 Valor Anual**")
                    st.dataframe(df_anual_row[kpis_da_planta], use_container_width=True, height=100)

                    # Metas futuras (espelhadas do formato)
                    st.markdown("**📅 Metas Mensais Futuras (Geral)**")
                    metas_fmt_ord = metas_fmt.reindex(index=kpis_da_planta, columns=MESES)

                    def _format_table(x):
                        out = x.copy()
                        for kpi in out.index:
                            if is_spoilage(kpi):
                                out.loc[kpi] = out.loc[kpi].map(lambda z: f"{float(z):.2f}%")
                            else:
                                out.loc[kpi] = out.loc[kpi].map(lambda z: f"{float(z):.3f}")
                        return out

                    st.dataframe(_format_table(metas_fmt_ord), use_container_width=True, height=420)

                else:
                    # Consolidação normal (respeitando bloqueios por KPI)
                    info_msgs = []
                    for kpi in kpis_da_planta:
                        if len(bloqueios_por_kpi[kpi]) > 0:
                            info_msgs.append(f"• {kpi}: não consolidado (formatos bloqueados: {', '.join(sorted(bloqueios_por_kpi[kpi]))})")
                    if info_msgs:
                        st.warning("Regras de consolidação aplicadas:\n" + "\n".join(info_msgs))

                    geral_coef_anual = {}
                    geral_metas = pd.DataFrame(0.0, index=kpis_da_planta, columns=MESES)

                    for kpi in kpis_da_planta:
                        formatos_validos_kpi = [f for f in nomes_formatos if f not in bloqueios_por_kpi[kpi]]
                        if len(formatos_validos_kpi) == 0:
                            geral_coef_anual[kpi] = 0.0
                            geral_metas.loc[kpi, :] = 0.0
                            continue

                        vol_total = pd.Series(0.0, index=MESES)
                        realizado_ytd_total = 0.0
                        total_fy_total = 0.0

                        for f in formatos_validos_kpi:
                            vol_mensal = volumes[f]['Volume Total'].astype(float).reindex(MESES).fillna(0.0)
                            vol_total += vol_mensal

                            serie = aops[f].loc[kpi].astype(float).reindex(MESES + ['FY']).fillna(0.0)
                            fy = float(serie.get('FY', 0.0))
                            serie_mes = serie.reindex(MESES).fillna(0.0)

                            if is_spoilage(kpi):
                                realizado_ytd_total += ((serie_mes[colunas_ytd] / 100.0) * vol_mensal[colunas_ytd]).sum()
                                total_fy_total += (fy / 100.0) * vol_mensal.sum()
                            else:
                                realizado_ytd_total += (serie_mes[colunas_ytd] * vol_mensal[colunas_ytd]).sum()
                                total_fy_total += fy * vol_mensal.sum()

                        if total_fy_total <= realizado_ytd_total:
                            geral_coef_anual[kpi] = 0.0
                            geral_metas.loc[kpi, :] = 0.0
                            continue

                        saldo_restante = total_fy_total - realizado_ytd_total
                        vol_fut = vol_total[colunas_futuro].sum()

                        if vol_fut <= 0.0:
                            geral_coef_anual[kpi] = 0.0
                            geral_metas.loc[kpi, :] = 0.0
                            continue

                        estimado_geral = pd.Series(0.0, index=colunas_futuro)
                        for f in formatos_validos_kpi:
                            vol_mensal = volumes[f]['Volume Total'].astype(float).reindex(MESES).fillna(0.0)
                            serie_mes = aops[f].loc[kpi].astype(float).reindex(MESES).fillna(0.0)
                            if is_spoilage(kpi):
                                estimado_geral += (serie_mes[colunas_futuro] / 100.0) * vol_mensal[colunas_futuro]
                            else:
                                estimado_geral += (serie_mes[colunas_futuro]) * vol_mensal[colunas_futuro]

                        total_estimado = float(estimado_geral.sum())
                        if total_estimado <= 0.0:
                            base_prop = vol_total[colunas_futuro]
                            total_base = base_prop.sum()
                            if total_base <= 0.0:
                                metas_valor = pd.Series(0.0, index=colunas_futuro)
                            else:
                                proporcao = base_prop / total_base
                                metas_valor = proporcao * saldo_restante
                        else:
                            proporcao = (estimado_geral / total_estimado).fillna(0.0)
                            metas_valor = proporcao * saldo_restante

                        if is_spoilage(kpi):
                            metas_coef = (metas_valor / vol_total[colunas_futuro]).replace([np.inf, -np.inf], 0.0).fillna(0.0) * 100.0
                            geral_coef_anual[kpi] = (saldo_restante / max(vol_fut, 1e-9)) * 100.0
                        else:
                            metas_coef = (metas_valor / vol_total[colunas_futuro]).replace([np.inf, -np.inf], 0.0).fillna(0.0)
                            geral_coef_anual[kpi] = (saldo_restante / max(vol_fut, 1e-9))

                        geral_metas.loc[kpi, colunas_futuro] = metas_coef.values

                    # Valor Anual (KPIs nas colunas; 1 linha)
                    def _fmt_val(kpi, v):
                        return f"{float(v):.2f}%" if is_spoilage(kpi) else f"{float(v):.3f}"
                    linha_geral = {k: _fmt_val(k, geral_coef_anual.get(k, 0.0)) for k in kpis_da_planta}
                    df_anual_row_geral = pd.DataFrame([linha_geral], index=["Necessário (FY)"])

                    st.markdown("**📊 Valor Anual**")
                    st.dataframe(df_anual_row_geral[kpis_da_planta], use_container_width=True, height=100)

                    # Metas futuras (Geral)
                    def _format_table(x):
                        out = x.copy()
                        for kpi in out.index:
                            if is_spoilage(kpi):
                                out.loc[kpi] = out.loc[kpi].map(lambda z: f"{float(z):.2f}%")
                            else:
                                out.loc[kpi] = out.loc[kpi].map(lambda z: f"{float(z):.3f}")
                        return out
                    st.markdown("**📅 Metas Mensais Futuras (Geral)**")
                    st.dataframe(_format_table(geral_metas.reindex(index=kpis_da_planta, columns=MESES)),
                                 use_container_width=True, height=420)

            # ---------- ABAS DE FORMATO (depois do Geral) ----------
            for pos, formato in enumerate(nomes_formatos, start=1):
                with abas[pos]:
                    st.subheader(f"Formato: {formato}")
                    chips_meses(colunas_ytd, colunas_futuro)

                    coef_anual_fmt = resultados_por_formato[formato]['coef_anual_necessario'].copy()
                    fy_series = aops[formato]['FY'].astype(float).reindex(kpis_da_planta).fillna(0.0)
                    metas_fmt = resultados_por_formato[formato]['metas_futuras'].copy()

                    # (NOVO) manter AOP quando resultado calculado é melhor que AOP
                    for kpi in kpis_da_planta:
                        if _resultado_melhor_que_aop(metas_fmt.loc[kpi], aops_show[formato].loc[kpi], kpi):
                            metas_fmt.loc[kpi, colunas_futuro] = aops_show[formato].loc[kpi, colunas_futuro].values
                            aop_mantido_melhor_logs.append((formato, kpi))

                    # KPIs em que necessário > FY → aplicar AOP (Exibição) e logar aviso
                    substituir_por_aop = fy_series.index[(coef_anual_fmt.fillna(0.0) > fy_series.fillna(0.0))].tolist()
                    if len(colunas_futuro) > 0 and substituir_por_aop:
                        for kpi in substituir_por_aop:
                            metas_fmt.loc[kpi, colunas_futuro] = aops_show[formato].loc[kpi, colunas_futuro].values
                            aop_melhor_logs.append((formato, kpi))

                    # Valor Anual (colunas = KPIs; 1 linha) — substitui exibição por FY quando necessário > FY
                    coef_anual_display = coef_anual_fmt.copy()
                    for kpi in substituir_por_aop:
                        coef_anual_display.loc[kpi] = fy_series.loc[kpi]

                    def _fmt_val(kpi, v):
                        return f"{float(v):.2f}%" if is_spoilage(kpi) else f"{float(v):.3f}"
                    linha_fmt = {k: _fmt_val(k, coef_anual_display.get(k, 0.0)) for k in kpis_da_planta}
                    df_anual_row_fmt = pd.DataFrame([linha_fmt], index=["Necessário (FY)"])

                    st.markdown("**📊 Valor Anual — KPIs como colunas (Formato)**")
                    st.dataframe(df_anual_row_fmt[kpis_da_planta], use_container_width=True, height=100)

                    # Metas Mensais Futuras (por KPI)
                    st.markdown("**📅 Metas Mensais Futuras (por KPI)**")
                    metas_fmt_ord = metas_fmt.reindex(index=kpis_da_planta, columns=MESES)
                    def _format_table(x):
                        out = x.copy()
                        for kpi in out.index:
                            if is_spoilage(kpi):
                                out.loc[kpi] = out.loc[kpi].map(lambda z: f"{float(z):.2f}%")
                            else:
                                out.loc[kpi] = out.loc[kpi].map(lambda z: f"{float(z):.3f}")
                        return out
                    st.dataframe(_format_table(metas_fmt_ord), use_container_width=True, height=420)

            # --- AVISOS GERAIS ---
            if aop_melhor_logs:
                msg_por_formato = {}
                for formato, kpi in aop_melhor_logs:
                    msg_por_formato.setdefault(formato, []).append(kpi)
                linhas = [f"• {fmt}: " + ", ".join(kpis) for fmt, kpis in msg_por_formato.items()]
                st.info("🔒 **AOP (Exibição) aplicado porque o 'necessário' superou o FY**:\n" + "\n".join(linhas))

            if aop_mantido_melhor_logs:
                msg_por_formato2 = {}
                for formato, kpi in aop_mantido_melhor_logs:
                    msg_por_formato2.setdefault(formato, []).append(kpi)
                linhas2 = [f"• {fmt}: " + ", ".join(kpis) for fmt, kpis in msg_por_formato2.items()]
                st.info("🟦 **AOP (Exibição) mantido no futuro porque o realizado ficou melhor que o AOP**:\n" + "\n".join(linhas2))

        st.success("✅ Cálculos concluídos com sucesso!")

    st.markdown("---")
    st.markdown(
        f"<div style='text-align: center; color: gray;'>Calculadora Reforecast v10.0 | {datetime.now().year}</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
