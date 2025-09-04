import streamlit as st
import pandas as pd
from datetime import datetime
import numpy as np
from pathlib import Path


KPIS_CANS = ['Spoilage']
KPIS_ENDS = ['Spoilage']

PLANTAS_CONFIG = {}
# Plantas de latas
for planta in ['ARBA', 'BRBR', 'BR3R', 'BRJC', 'BRPA', 'BRET', 'BRPE', 'BRFR', 'BRAC', 'PYAS', 'CLSA']:
    PLANTAS_CONFIG[planta] = {'tipo': 'Cans', 'kpis': KPIS_CANS}
# Plantas de tampas
for planta in ['BRAM', 'PYAST', 'BRPET', 'BR3RT']:
    PLANTAS_CONFIG[planta] = {'tipo': 'Ends', 'kpis': KPIS_ENDS}

MESES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
         'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']


def validar_dados(vol_df, aop_df):
    erros = []
    if (vol_df < 0).any().any():
        erros.append("Volume de produção não pode ser negativo")
    if pd.isna(aop_df['FY']).any() or (aop_df['FY'] <= 0).any():
        erros.append("Target anual (FY) deve ser preenchido e maior que zero")
    return erros


def main():
    st.set_page_config(
        page_title="Calculadora de Reforecast",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # --- VARIÁVEIS DE CORES E LOGO ---
    COR_PRIMARIA = "#1140FE"
    COR_SECUNDARIA = "#0029B3"
    COR_FUNDO = "#FFFFFF"
    COR_FUNDO_SECUNDARIO = "#F8F9FB"
    COR_BORDA_CARD = "#E6EAF1"
    COR_TEXTO = "#333333"

    # Cores específicas das abas
    COR_TAB_ATIVA_BG = COR_PRIMARIA
    COR_TAB_ATIVA_TX = "#FFFFFF"
    COR_TAB_INATIVA_BG = "#EEF2FF"
    COR_TAB_INATIVA_TX = "#3B3B3B"
    COR_TAB_BORDA = "#D6DAE3"
    COR_TAB_HOVER_BG = "#E8EDFF"

    BASE_DIR = Path(__file__).parent
    LOGO_URL = BASE_DIR / "logo.png"  # ajuste o nome/extensão se necessário

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
        st.subheader("AOP exibido apenas quando o cálculo superaria o FY")

    st.markdown("---")

    # --- Passo 1: Seleção da Planta ---
    st.header("1️⃣ Seleção da Planta")
    with st.container(border=True):
        col1, col2 = st.columns([2, 1])
        with col1:
            lista_plantas = sorted(list(PLANTAS_CONFIG.keys()))
            planta_selecionada = st.selectbox(
                "Escolha a planta", options=[""] + lista_plantas,
                format_func=lambda x: "Selecione..." if x == "" else x
            )
        if not planta_selecionada:
            st.info("👆 Selecione uma planta para continuar")
            st.stop()
        with col2:
            tipo_planta = PLANTAS_CONFIG[planta_selecionada]['tipo']
            st.metric("Tipo de Planta", tipo_planta)
    kpis_da_planta = PLANTAS_CONFIG[planta_selecionada]['kpis']

    # --- Passo 2: Configurações do Cálculo ---
    st.header("2️⃣ Configurações do Cálculo")
    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            mes_reforecast = st.select_slider(
                "Mês do Reforecast", options=MESES, value='Junho',
                help="Mês final do período YTD"
            )
        idx_mes_reforecast = MESES.index(mes_reforecast)
        colunas_ytd = MESES[:idx_mes_reforecast + 1]
        colunas_futuro = MESES[idx_mes_reforecast + 1:]
        with col2:
            st.metric("Meses YTD", len(colunas_ytd))
        with col3:
            st.metric("Meses Futuros", len(colunas_futuro))

    # --- Passo 3: Configuração de Formatos ---
    st.header("3️⃣ Configuração de Formatos")
    with st.container(border=True):
        num_formatos = st.number_input("Número de formatos", min_value=1, max_value=10, value=2)
        cols_nomes = st.columns(min(num_formatos, 4))
        nomes_formatos = [
            st.text_input(f"Formato {i+1}", value=f"Formato_{i+1}", key=f"formato_nome_{i}")
            for i in range(num_formatos)
        ]

    st.markdown("---")

    # --- Passo 4: Dados por Formato ---
    st.header("4️⃣ Dados de Entrada por Formato")
    dados_formatos = {}
    tabs_formatos = st.tabs(nomes_formatos)

    for i, tab in enumerate(tabs_formatos):
        with tab:
            formato_atual = nomes_formatos[i]
            st.subheader(f"📊 {formato_atual}")

            # Volume
            st.markdown("##### 📈 Volume de Produção")
            df_volume = pd.DataFrame(0.0, index=["Volume Total"], columns=MESES)
            df_volume_editado = st.data_editor(
                df_volume, key=f"volume_{i}", use_container_width=True, num_rows="fixed"
            )

            # AOP principal (contém FY)
            st.markdown("##### 🎯 Metas AOP - Spoilage (%)")
            config_colunas = {}
            df_aop = pd.DataFrame(index=kpis_da_planta, columns=MESES + ['FY'])
            for mes in colunas_ytd:
                config_colunas[mes] = st.column_config.NumberColumn(
                    f"{mes} (%)", format="%.3f", help="Percentual REAL já ocorrido"
                )
                df_aop[mes] = 0.0
            for mes in colunas_futuro:
                config_colunas[mes] = st.column_config.NumberColumn(
                    f"{mes} (%)", format="%.3f", help="Meta planejada em %"
                )
                df_aop[mes] = 0.0
            config_colunas['FY'] = st.column_config.NumberColumn(
                "Target Anual (FY) (%)", format="%.3f", required=True, help="Meta anual total"
            )
            df_aop['FY'] = 0.0
            df_aop_editado = st.data_editor(
                df_aop, column_config=config_colunas, key=f"aop_{i}",
                use_container_width=True, num_rows="fixed"
            )

            # NOVA tabela: AOP (Exibição) — 12 meses (sem FY)
            st.markdown("##### 🧷 AOP (Exibição) – valores a mostrar quando cálculo > FY")
            df_aop_show = pd.DataFrame(index=kpis_da_planta, columns=MESES)
            cfg_show = {
                mes: st.column_config.NumberColumn(
                    f"{mes} (%)", format="%.3f", help="Percentual a exibir em caso de travamento visual"
                ) for mes in MESES
            }
            df_aop_show.loc[:, :] = 0.0
            df_aop_show_editado = st.data_editor(
                df_aop_show, column_config=cfg_show, key=f"aop_show_{i}",
                use_container_width=True, num_rows="fixed"
            )

            dados_formatos[formato_atual] = {
                'volume': df_volume_editado,
                'aop': df_aop_editado,
                'aop_show': df_aop_show_editado
            }

    st.markdown("---")

    # --- Passo 5: Cálculo e Resultados ---
    st.header("5️⃣ Cálculo e Resultados")
    if st.button("🚀 Calcular Reforecast", type="primary", use_container_width=True):

        with st.spinner("Consolidando dados e executando cálculos... Por favor, aguarde."):

            # ETAPA 1: Consolidar inputs dos formatos
            lista_dfs_volume = []
            lista_dfs_coef = []
            lista_dfs_aop_show = []

            for formato in nomes_formatos:
                df_vol_formato = dados_formatos[formato]['volume'].T.rename(columns={"Volume Total": formato})
                df_aop_formato = dados_formatos[formato]['aop'].T.rename(columns={"Spoilage": formato})
                df_aop_show_formato = dados_formatos[formato]['aop_show'].T.rename(columns={"Spoilage": formato})

                lista_dfs_volume.append(df_vol_formato)
                lista_dfs_coef.append(df_aop_formato)
                lista_dfs_aop_show.append(df_aop_show_formato)

            df_volume_all = pd.concat(lista_dfs_volume, axis=1)
            df_coef_all = pd.concat(lista_dfs_coef, axis=1)
            df_aop_show_all = pd.concat(lista_dfs_aop_show, axis=1)

            # ---------- VERIFICAÇÃO POR FORMATO ----------
            # Se YTD líquido > FY líquido do formato, remover do cálculo e avisar
            formatos_ultrapassados = []
            for fmt in nomes_formatos:
                vol_liq_ytd_fmt = ((df_coef_all.loc[colunas_ytd, fmt] / 100.0) * df_volume_all.loc[colunas_ytd, fmt]).sum()
                vol_liq_total_fy_fmt = (df_coef_all.loc['FY', fmt] / 100.0) * df_volume_all[fmt].sum()
                if vol_liq_ytd_fmt > vol_liq_total_fy_fmt:
                    formatos_ultrapassados.append(fmt)

            formatos_validos = [f for f in nomes_formatos if f not in formatos_ultrapassados]

            if len(formatos_validos) == 0:
                st.error("❌ FY de todos os formatos já foi ultrapassado pelo YTD. Cálculo não realizado.")
                st.stop()

            # Trabalhar a partir daqui apenas com os formatos válidos
            df_volume = df_volume_all[formatos_validos].copy()
            df_coef = df_coef_all[formatos_validos].copy()
            df_aop_show = df_aop_show_all[formatos_validos].copy()

            # Só calcula o 'Geral' se NENHUM formato estiver ultrapassado
            calcular_geral = (len(formatos_ultrapassados) == 0)
            if calcular_geral:
                df_volume['Geral'] = df_volume.sum(axis=1)

            # ---------- CÁLCULO NORMAL (inalterado) ----------
            df_vol_liq = (df_coef.loc[MESES] / 100.0) * df_volume
            if calcular_geral:
                df_vol_liq['Geral'] = df_vol_liq.sum(axis=1)
                coef_geral_mensal = (df_vol_liq['Geral'] / df_volume['Geral']) * 100.0
                df_coef['Geral'] = coef_geral_mensal

            valor_liq_ytd = df_vol_liq.loc[colunas_ytd].sum()
            volume_total_fy = df_volume.sum()
            valor_liq_total_fy = (df_coef.loc['FY'] / 100.0) * volume_total_fy

            if calcular_geral:
                valor_liq_total_fy['Geral'] = valor_liq_total_fy.drop('Geral').sum()
                df_coef.loc['FY', 'Geral'] = (valor_liq_total_fy['Geral'] / volume_total_fy['Geral']) * 100.0

            saldo_restante = valor_liq_total_fy - valor_liq_ytd
            valor_total_futuro = df_volume.loc[colunas_futuro].sum()
            coeficientes_necessarios = (saldo_restante / valor_total_futuro) * 100.0

            df_coef_futuro = df_coef.loc[colunas_futuro]
            df_volume_futuro = df_volume.loc[colunas_futuro]
            df_spoilage_estimado = (df_coef_futuro / 100.0) * df_volume_futuro
            total_spoilage_estimado = df_spoilage_estimado.sum()
            df_proporcao_spoilage = df_spoilage_estimado.div(total_spoilage_estimado, axis='columns').fillna(0.0)
            df_orcamento_real_futuro = df_proporcao_spoilage.mul(saldo_restante, axis='columns')
            df_coef_final_mensal = (df_orcamento_real_futuro / df_volume_futuro) * 100.0

        # --- AVISOS: formatos que “performaram melhor que o FY” (cálculo > FY) ---
        formatos_para_exibir_aop = []
        for fmt in df_coef.columns:
            if fmt == 'Geral':
                continue
            nec = float(coeficientes_necessarios.get(fmt, np.nan))
            fy = float(df_coef.loc['FY', fmt])
            if pd.notna(nec) and nec > fy:
                formatos_para_exibir_aop.append(fmt)

        if formatos_ultrapassados:
            msg = "FY ultrapassado no(s) formato(s): " + ", ".join(formatos_ultrapassados)
            if len(formatos_validos) > 0:
                msg += f". Cálculo realizado apenas para: {', '.join(formatos_validos)}. Consolidado 'Geral' não foi calculado."
            st.warning(msg)

        if formatos_para_exibir_aop:
            st.warning("🔒 Os formatos a seguir performaram melhor  que o AOP; assim, mantemos a exibição dos valores do AOP. "
                       + ", ".join(formatos_para_exibir_aop))
        else:
            if not formatos_ultrapassados:
                st.success("✅ Cálculos concluídos com sucesso!")

        # --- RESULTADOS (com camada de EXIBIÇÃO quando necessário) ---

        # 1) Quadro anual (mostra FY para os que travam, e Necessário para o restante)
        coef_anuais_display = coeficientes_necessarios.copy()
        for fmt in formatos_para_exibir_aop:
            coef_anuais_display[fmt] = df_coef.loc['FY', fmt]  # mostra FY (AOP) no lugar do Necessário

        st.subheader("📊 Resultado 1: Coeficiente Anual (exibindo AOP quando cálculo > FY)")
        st.dataframe(pd.DataFrame(coef_anuais_display, columns=['Coeficiente Anual (%)']).T.style.format("{:.3f}%"),
                     use_container_width=True)

        # 2) Metas mensais futuras — para os “travados visualmente”, mostrar AOP (Exibição)
        df_coef_final_mensal_display = df_coef_final_mensal.copy()
        if len(colunas_futuro) > 0:
            for fmt in formatos_para_exibir_aop:
                if (fmt in df_coef_final_mensal_display.columns) and (fmt in df_aop_show.columns):
                    # reindex garante que meses batem; NaN vira 0.0 aqui apenas para exibição
                    aop_show_future = df_aop_show.reindex(index=MESES).loc[colunas_futuro, fmt].astype(float).fillna(0.0)
                    df_coef_final_mensal_display.loc[colunas_futuro, fmt] = aop_show_future.values

        st.subheader("📅 Resultado 2: Metas Mensais Futuras (%)")
        st.caption("Observação: quando cálculo > FY, exibimos os valores da tabela 'AOP (Exibição)' apenas para aquele formato. O 'Geral' permanece calculado normalmente.")
        if not df_coef_final_mensal_display.empty:
            st.dataframe(df_coef_final_mensal_display.style.format("{:.3f}%"), use_container_width=True)
        else:
            st.info("Não há meses futuros no recorte selecionado.")

    st.markdown("---")
    st.markdown(
        f"<div style='text-align: center; color: gray;'>Calculadora Reforecast v9.3 | {datetime.now().year}</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
