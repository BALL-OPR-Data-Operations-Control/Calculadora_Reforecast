import streamlit as st
import pandas as pd
from datetime import datetime
import numpy as np
from pathlib import Path
import base64 # Importa a biblioteca para codificar imagens

# --- HELPERS DE ESTILO ---
def highlight_zero(val):
    try:
        # Tenta converter para float e verifica se é zero
        return "background-color: rgba(255, 0, 0, 0.18);" if float(val) == 0 else ""
    except (TypeError, ValueError):
        # Ignora erros se o valor não for numérico
        return ""

def style_metas_with_overrides(df: pd.DataFrame, overridden_set: set):
    """
    Estilo para as 'Metas Mensais Futuras':
    - Linhas (KPIs) que repetiram o AOP (overridden_set) ficam verdes suaves.
    - Células == 0 ficam vermelhas, exceto nas linhas verdes.

    Observação: Alguns KPIs podem ter sido renomeados (ex.: GAS -> 'Thermal (kwh/000)').
    Por isso, intersectamos overridden_set com o índice real do df.
    """
    # Cria um DataFrame de estilos vazio com o mesmo formato do original
    styles = pd.DataFrame("", index=df.index, columns=df.columns)

    # Garante que só tentamos estilizar linhas que realmente existem no df
    present_overrides = set(overridden_set) & set(df.index)

    # pinta de VERDE as linhas que repetiram o AOP
    if present_overrides:
        styles.loc[list(present_overrides), :] = "background-color: rgba(0, 200, 0, 0.18); color: #0b3d0b;"

    # pinta de VERMELHO as células == 0, exceto nas linhas verdes
    mask_zero = df.eq(0) # Máscara booleana para encontrar zeros
    if present_overrides:
        mask_zero.loc[list(present_overrides), :] = False  # não sobrescrever o verde

    # Aplica a máscara de zeros (vermelho)
    styles = styles.mask(mask_zero, "background-color: rgba(255, 0, 0, 0.18); color: #7a0000;")

    return styles


def style_metas_basic(df: pd.DataFrame):
    """Versão simples (quando não há overrides): pinta zeros de vermelho suave."""
    styles = pd.DataFrame("", index=df.index, columns=df.columns)
    # Aplica a máscara de zeros (vermelho)
    styles = styles.mask(df.eq(0), "background-color: rgba(255, 0, 0, 0.18); color: #7a0000;")
    return styles

# --- NOVA FUNÇÃO HELPER ---
# Esta função lê um arquivo de imagem e o converte para texto (base64)
def get_image_as_base64(path: Path):
    """Lê uma imagem e a converte para base64, para embutir no HTML/CSS."""
    try:
        with open(path, "rb") as f:
            data = f.read()
        # Codifica os dados binários da imagem para texto base64
        return base64.b64encode(data).decode()
    except IOError:
        # Se não encontrar a imagem, retorna uma string vazia e avisa o usuário
        st.error(f"Erro: Imagem não encontrada no caminho: {path}")
        return ""

# --- Listas de KPIs para a ENTRADA de dados ---
# Define os KPIs de entrada para plantas de "Cans" (Latas)
KPIS_CANS_INPUT = [
    'Gas (m³/000) / (kg/000)', 'Ink Usage (kg/000)', 'Inside Spray Usage(kg/000)', 'Metal Can (kg/000)','Scrap (kg/000)', 'Spoilage(%)',
    'Variable Light (kwh/000)- Fora Ponta',
    'Variable Light (kwh/000)- Ponta',
    'Varnish Usage (kg/000)',
    'Water & Sewer (m³/000)'
]

# Define os KPIs de entrada para plantas de "Ends" (Tampas)
KPIS_ENDS_INPUT = [
    'Metal End (kg/000)','Spoilage (%)','Tab Scrap (kg/000)','Compound Usage (kg/000)',
    'Variable Light (kwh/000)- Fora Ponta',
    'Variable Light (kwh/000)- Ponta',
    'Water & Sewer (m³/000)',
    'Metal Tab (kg/000)','End Scrap (kg/000)'
]

# -------------------------------
# CONFIGURAÇÃO DE GÁS
# -------------------------------
# Fatores de conversão (m³/kg para kwh)
GAS_FACTORS = {
    'GLP': 12.78,
    'GN': 10.76
}
# Mapeia qual planta usa qual tipo de gás
PLANTAS_GAS_TIPO = {
    'BRAC': 'GLP',
    'BRFR': 'GLP',
    'PYAS': 'GLP',
}
GAS_KPI_NAME = 'Gas (m³/000) / (kg/000)' # Nome interno/de entrada do KPI
GAS_KPI_NAME_OUTPUT = 'Thermal (kwh/000)' # <<< ALTERADO: Novo nome para exibição no resultado

# -------------------------------


# --- Listas de KPIs para a ORDEM da exibição final ---
# Ordem final dos KPIs de "Cans" (usando o nome de saída do gás)
KPIS_CANS = [
    GAS_KPI_NAME_OUTPUT, # <<< ALTERADO: Usa o novo nome de output
    'Ink Usage (kg/000)', 'Inside Spray Usage(kg/000)', 'Metal Can (kg/000)','Scrap (kg/000)', 'Spoilage(%)',
    'Variable Light (kwh/000)', 'Varnish Usage (kg/000)',
    'Water & Sewer (m³/000)'
]

# Ordem final dos KPIs de "Ends"
KPIS_ENDS = [
    'Metal End (kg/000)','Spoilage (%)','Tab Scrap (kg/000)','Compound Usage (kg/000)',
    'Variable Light (kwh/000)',
    'Water & Sewer (m³/000)',
    'Metal Tab (kg/000)','End Scrap (kg/000)'
]

# Dicionário principal de configuração
PLANTAS_CONFIG = {}
# Mapeia plantas ao seu tipo ('Cans') e KPIs de entrada
for planta in ['ARBA', 'BRBR', 'BR3R', 'BRJC', 'BRPA', 'BRET', 'BRPE', 'BRFR', 'BRAC', 'PYAS', 'CLSA']:
    PLANTAS_CONFIG[planta] = {'tipo': 'Cans', 'kpis': KPIS_CANS_INPUT}
# Mapeia plantas ao seu tipo ('Ends') e KPIs de entrada
for planta in ['BRAM', 'PYAST', 'BRPET', 'BR3RT']:
    PLANTAS_CONFIG[planta] = {'tipo': 'Ends', 'kpis': KPIS_ENDS_INPUT}

# MESES abreviados (usado como colunas padrão)
MESES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
         'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']


def agregar_energia(df: pd.DataFrame, final_kpi_order: list) -> pd.DataFrame:
    """Soma 'Ponta' e 'Fora Ponta' em 'Variable Light (kwh/000)'."""
    df = df.copy()
    kpi_ponta = 'Variable Light (kwh/000)- Ponta'
    kpi_fora_ponta = 'Variable Light (kwh/000)- Fora Ponta'
    kpi_unificado = 'Variable Light (kwh/000)'

    # Cria uma cópia da ordem final para poder remover itens
    order_copy = final_kpi_order[:]
    if kpi_unificado in order_copy:
        order_copy.remove(kpi_unificado)

    # Adiciona os KPIs de energia (se existirem) para reindexação temporária
    _ = order_copy + [kpi for kpi in [kpi_ponta, kpi_fora_ponta, kpi_unificado] if kpi in df.index or kpi in df.columns]

    # Verifica se os KPIs existem no índice (linhas)
    if kpi_ponta in df.index and kpi_fora_ponta in df.index:
        soma_energia = df.loc[kpi_ponta] + df.loc[kpi_fora_ponta]
        df.loc[kpi_unificado] = soma_energia
        df = df.drop(index=[kpi_ponta, kpi_fora_ponta]) # Remove os KPIs antigos

    # Verifica se os KPIs existem nas colunas
    elif kpi_ponta in df.columns and kpi_fora_ponta in df.columns:
        soma_energia = df[kpi_ponta] + df[kpi_fora_ponta]
        df[kpi_unificado] = soma_energia
        df = df.drop(columns=[kpi_ponta, kpi_fora_ponta]) # Remove os KPIs antigos

    # Reordena usando a ordem final original (seja por linha ou coluna)
    if set(df.index).issuperset(set(final_kpi_order)):
        valid_order = [item for item in final_kpi_order if item in df.index]
        return df.reindex(index=valid_order).dropna(how='all')
    elif set(df.columns).issuperset(set(final_kpi_order)):
        valid_order = [item for item in final_kpi_order if item in df.columns]
        return df.reindex(columns=valid_order).dropna(how='all')
    return df


def validar_dados(vol_df, aop_df):
    """Verifica se os dados de entrada são válidos (ex: sem negativos)."""
    erros = []
    if (vol_df < 0).any().any():
        erros.append("Volume de produção não pode ser negativo")
    if pd.isna(aop_df['FY']).any():
        erros.append("Há FY não informado (NaN). Preencha com 0 quando não houver meta.")
    return erros

def get_plant_store(planta: str):
    """Obtém/cria o estado da sessão (dados salvos) para uma planta específica."""
    # 'plant_store' é o "banco de dados" do app no st.session_state
    store = st.session_state.setdefault('plant_store', {})
    # Se a planta ainda não foi acessada, cria um dicionário padrão para ela
    if planta not in store:
        store[planta] = {
            'num_formatos': 2,
            'nomes_formatos': [f'Formato_{i+1}' for i in range(2)],
            'dados': {} # Onde os DataFrames de volume e aop serão salvos
        }
    return store[planta]

def set_plant_store(planta: str, plant_state: dict):
    """Salva o estado da sessão (dados) para uma planta."""
    st.session_state.setdefault('plant_store', {})
    st.session_state['plant_store'][planta] = plant_state

def _to_float_br(x):
    """Converte strings (formato BR: "1.000,50" ou "1.000") para float."""
    if isinstance(x, str):
        s = x.strip().replace(" ", "")
        if ',' in s:
            # Converte "1.000,50" para "1000.50"
            s = s.replace('.', '').replace(',', '.')
        try:
            return float(s)
        except Exception:
            return x # Retorna o original se falhar
    return x

def corrige_decimais_df(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica a conversão de decimal BR em todo o DataFrame."""
    return df.applymap(_to_float_br)

def renomear_gas_para_output(df: pd.DataFrame) -> pd.DataFrame:
    """Renomeia o KPI de Gás (entrada) para 'Thermal' (saída)."""
    df = df.copy()
    rename_map = {GAS_KPI_NAME: GAS_KPI_NAME_OUTPUT}
    # Renomeia se o nome do Gás estiver no índice (linhas)
    if GAS_KPI_NAME in df.index:
        df = df.rename(index=rename_map)
    # Renomeia se o nome do Gás estiver nas colunas
    if GAS_KPI_NAME in df.columns:
        df = df.rename(columns=rename_map)
    return df

def main():
    # Função principal da aplicação Streamlit
    st.set_page_config(
        page_title="Calculadora de Reforecast",
        page_icon="📈",
        layout="wide", # Layout largo para melhor visualização das tabelas
        initial_sidebar_state="expanded"
    )

    # Bloco de definição de variáveis de cores para o CSS
    COR_PRIMARIA = "#1140FE"
    COR_SECUNDARIA = "#0029B3"
    COR_FUNDO = "#FFFFFF"
    COR_FUNDO_SECUNDARIO = "#F8F9FB"
    COR_BORDA_CARD = "#E6EAF1"
    COR_TEXTO = "#333333"
    COR_CHIP_YTD = "#1140FE" # Cor dos meses passados
    COR_CHIP_FUT = "#B0B7C9" # Cor dos meses futuros
    COR_TAB_ATIVA_BG = COR_PRIMARIA
    COR_TAB_ATIVA_TX = "#FFFFFF"
    COR_TAB_INATIVA_BG = "#EEF2FF"
    COR_TAB_INATIVA_TX = "#3B3B3B"
    COR_TAB_BORDA = "#D6DAE3"
    COR_TAB_HOVER_BG = "#E8EDFF"

    # Define o diretório base para carregar arquivos (logos)
    BASE_DIR = Path(__file__).parent
    LOGO_URL = BASE_DIR / "logo.png"
    LOGO_BRANCO_URL = BASE_DIR / "logo_branco.png"

    # Carrega as imagens do logo em base64 (para embutir no CSS/HTML)
    logo_b64 = get_image_as_base64(LOGO_URL)
    logo_branco_b64 = get_image_as_base64(LOGO_BRANCO_URL)

    # Prepara o HTML para exibir os logos (um para modo claro, outro para escuro)
    logos_html = f"""
        <div class="logo-light">
            <img src="data:image/png;base64,{logo_b64}" width="150">
        </div>
        <div class="logo-dark">
            <img src="data:image/png;base64,{logo_branco_b64}" width="150">
        </div>
    """

    # Injeta CSS customizado para estilizar o app (cores, abas, botões, modo escuro)
    st.markdown(f"""
    <style>
        :root {{
            /* Variáveis de cor (Modo Claro) */
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
        /* Estilos gerais */
        .stApp {{ background-color: var(--cor-fundo); color: var(--cor-texto); }}
        h1, h2, h3, h4 {{ color: var(--cor-primaria); }}
        [data-testid="stSidebar"] {{ background-color: var(--cor-fundo-secundario); }}
        .logo-light {{ display: block; }} /* Logo claro visível por padrão */
        .logo-dark {{ display: none; }} /* Logo escuro escondido por padrão */

        /* Estilo Botão Primário */
        .stButton>button {{ border: none; background-color: var(--cor-primaria); color: white; border-radius: 8px; padding: 10px 20px; font-weight: 600; transition: .3s; }}
        .stButton>button:hover {{ background-color: var(--cor-secundaria); transform: scale(1.02); }}
        
        /* Estilo do st.container(border=True) */
        .st-emotion-cache-1r6slb0 {{ border: 1px solid var(--cor-borda-card); border-radius: 12px; padding: 1rem; background-color: var(--cor-fundo-secundario); box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
        
        /* Estilo das st.tabs */
        .stTabs [data-baseweb="tab-list"] {{ gap: 6px; }}
        .stTabs [data-baseweb="tab-list"] button {{ background-color: var(--cor-tab-inativa-bg); color: var(--cor-tab-inativa-tx); border: 1px solid var(--cor-tab-borda); border-bottom: none; padding: 8px 14px; border-radius: 10px 10px 0 0; box-shadow: none; }}
        .stTabs [data-baseweb="tab-list"] button:hover {{ background-color: var(--cor-tab-hover-bg); }}
        .stTabs [data-baseweb="tab-list"] button p {{ font-weight: 600; margin: 0; }}
        .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {{ background-color: var(--cor-tab-ativa-bg); color: var(--cor-tab-ativa-tx); border-color: var(--cor-tab-ativa-bg); }}
        .stTabs [data-baseweb="tab-highlight"] {{ background-color: transparent !important; }}
        .stTabs [data-baseweb="tab-panel"] {{ border: 1px solid var(--cor-tab-borda); border-top: 0; border-radius: 0 10px 10px 10px; padding: 1rem; background: var(--cor-fundo); }}
        
        /* Estilo dos "Chips" de meses */
        .chips {{ display: flex; gap: .4rem; flex-wrap: wrap; }}
        .chip {{ padding: .14rem .5rem; border-radius: 999px; font-size: .80rem; font-weight: 600; }}
        .chip-ytd {{ background: {COR_CHIP_YTD}; color: white; }}
        .chip-fut {{ background: {COR_CHIP_FUT}; color: white; }}

        /* Media Query para MODO ESCURO (Dark Mode) */
        @media (prefers-color-scheme: dark) {{
            :root {{
                /* Variáveis de cor (Modo Escuro) */
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
            .logo-light {{ display: none; }} /* Esconde logo claro */
            .logo-dark {{ display: block; }} /* Mostra logo escuro */
            /* Ajustes finos para modo escuro */
            [data-testid="stMetricLabel"], [data-testid="stMetricValue"] {{ color: var(--cor-texto) !important; }}
            [data-testid="stAlert"] {{ background-color: #2F3136 !important; color: #EAEAEA !important; border: 1px solid #4F545C !important; }}
            [data-testid="stAlert"] svg {{ fill: #EAEAEA !important; }}
        }}
    </style>
    """, unsafe_allow_html=True)

    # --- CABEÇALHO ---
    col_logo, col_title = st.columns([1, 4]) # Define o layout do cabeçalho
    with col_logo:
        st.markdown(logos_html, unsafe_allow_html=True) # Exibe o HTML do logo
        
    with col_title:
        st.title("Calculadora de Reforecast")
        st.subheader("Readequação ao AOP")

    st.markdown("---") # Linha divisória

    # --- SEÇÃO 1: SELEÇÃO DA PLANTA ---
    st.header("1️⃣ Seleção da Planta")
    with st.container(border=True): # Usa o container estilizado via CSS
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            lista_plantas = sorted(list(PLANTAS_CONFIG.keys()))
            # Dropdown para selecionar a planta
            planta_selecionada = st.selectbox(
                "Escolha a planta", options=[""] + lista_plantas,
                format_func=lambda x: "Selecione..." if x == "" else x,
                key="planta_select" # Chave global (não muda por planta)
            )
        # Para a execução se nenhuma planta for escolhida
        if not planta_selecionada:
            st.info("👆 Selecione uma planta para continuar")
            st.stop() # Interrompe o script
        
        # Exibe métricas (Tipo de Planta, Tipo de Gás)
        with col2:
            tipo_planta = PLANTAS_CONFIG[planta_selecionada]['tipo']
            st.metric("Tipo de Planta", tipo_planta)
        with col3:
            fator_gas = 1.0 # Fator padrão (se não usar gás)
            # Verifica se a planta selecionada usa o KPI de gás
            tem_kpi_gas = any(GAS_KPI_NAME in kpi for kpi in PLANTAS_CONFIG[planta_selecionada]['kpis'])
            if tem_kpi_gas:
                # Busca o tipo de gás e o fator de conversão
                tipo_gas = PLANTAS_GAS_TIPO.get(planta_selecionada, 'GN') # 'GN' como padrão
                fator_gas = GAS_FACTORS[tipo_gas]
                st.metric("Tipo de Gás", tipo_gas, help=f"Fator de conversão: {fator_gas}")

    # Carrega as configurações e o estado da sessão da planta selecionada
    kpis_da_planta = PLANTAS_CONFIG[planta_selecionada]['kpis']
    plant_state = get_plant_store(planta_selecionada) # 'plant_state' armazena os dados salvos

    # --- SEÇÃO 2: MÊS DO REFORECAST ---
    st.header("2️⃣ Configurações do Cálculo")
    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            # Busca o mês salvo no 'plant_state' ou usa 'Jun' como padrão
            mes_default = plant_state.get('mes_reforecast', 'Jun')
            # Slider para selecionar o mês de corte
            mes_reforecast = st.select_slider(
                "Mês do Reforecast", options=MESES, value=mes_default,
                help="Mês final do período YTD",
                key=f"{planta_selecionada}_mes_reforecast" # Chave única por planta
            )
            # Salva a escolha do mês no estado da sessão
            plant_state['mes_reforecast'] = mes_reforecast
            set_plant_store(planta_selecionada, plant_state)
        
        # Define as listas de meses YTD (passado) e Futuro com base no corte
        idx_mes_reforecast = MESES.index(mes_reforecast)
        colunas_ytd = MESES[:idx_mes_reforecast + 1] # Inclui o mês de reforecast
        colunas_futuro = MESES[idx_mes_reforecast + 1:] # Apenas meses seguintes
        
        # Exibe a contagem de meses YTD e Futuros
        with col2:
            st.metric("Meses YTD", len(colunas_ytd))
        with col3:
            st.metric("Meses Futuros", len(colunas_futuro))

    # Função local para exibir os meses como "chips" coloridos (YTD vs Futuro)
    def chips_meses(ytd_cols, fut_cols, titulo="Meses (YTD | Futuro)"):
        chips = "".join([f"<span class='chip chip-ytd'>{m}</span>" for m in ytd_cols] +
                        [f"<span class='chip chip-fut'>{m}</span>" for m in fut_cols])
        st.markdown(f"**{titulo}** \n<div class='chips'>{chips}</div>", unsafe_allow_html=True)

    # --- SEÇÃO 3: CONFIGURAÇÃO DE FORMATOS ---
    st.header("3️⃣ Configuração de Formatos")
    with st.container(border=True):
        # Input para o número de formatos (produtos)
        num_formatos = st.number_input(
            "Número de formatos", min_value=1, max_value=10,
            value=int(plant_state['num_formatos']), # Carrega o valor salvo
            key=f"{planta_selecionada}_num_formatos" # Chave única
        )
        plant_state['num_formatos'] = int(num_formatos)
        
        # Cria colunas dinâmicas para os nomes (máx 4 por linha)
        cols_nomes = st.columns(min(num_formatos, 4))
        nomes_guardados = plant_state.get('nomes_formatos', [])
        novos_nomes = []
        
        # Loop para criar campos de texto para nomear cada formato
        for i in range(num_formatos):
            default_nome = nomes_guardados[i] if i < len(nomes_guardados) else f"Formato_{i+1}"
            with cols_nomes[i % len(cols_nomes)]: # Distribui os inputs nas colunas
                nome_i = st.text_input(f"Formato {i+1}", value=default_nome, key=f"{planta_selecionada}_formato_nome_{i}")
            novos_nomes.append(nome_i)
        
        # Salva os nomes dos formatos no estado da sessão
        plant_state['nomes_formatos'] = novos_nomes
        set_plant_store(planta_selecionada, plant_state)

    st.markdown("---")

    # --- SEÇÃO 4: ENTRADA DE DADOS POR FORMATO ---
    st.header("4️⃣ Dados de Entrada por Formato")
    dados_formatos = {} # Dicionário temporário para os cálculos
    tabs_formatos = st.tabs(plant_state['nomes_formatos']) # Cria abas para cada formato

    # Loop em cada aba de formato
    for i, tab in enumerate(tabs_formatos):
        with tab:
            formato_atual = plant_state['nomes_formatos'][i]
            st.subheader(f"{formato_atual}")
            chips_meses(colunas_ytd, colunas_futuro) # Mostra a divisão YTD/Futuro
            st.write("")
            
            # Carrega os dados salvos para este formato (índice 'i')
            dados_salvos = plant_state['dados'].get(i, {})
            
            # Tabela editável (data_editor) para o Volume de Produção
            st.markdown("##### 📈 Volume de Produção")
            # Carrega o DF salvo ou cria um novo DF com zeros
            df_volume_default = dados_salvos.get('volume', pd.DataFrame(0.0, index=["Volume Total"], columns=MESES))
            df_volume_editado = st.data_editor(df_volume_default, key=f"{planta_selecionada}_volume_{i}", use_container_width=True, num_rows="fixed")
            # Corrige decimais (ex: '1.000,5' -> 1000.5) após a edição
            df_volume_editado = corrige_decimais_df(df_volume_editado).astype(float)
            
            # --- LÓGICA CORRIGIDA ---
            # Tabela editável para os Coeficientes YTD (o que realmente aconteceu)
            st.markdown("##### 🎯 Coeficientes YTD + Ciclo Anterior")
            dados_salvos_aop = dados_salvos.get('aop', pd.DataFrame(index=kpis_da_planta, columns=MESES).fillna(0.0))
            df_aop_para_editar = dados_salvos_aop.copy()
            # Remove a coluna 'FY' (meta) desta tabela de edição (ela vem da tabela abaixo)
            if 'FY' in df_aop_para_editar.columns:
                df_aop_para_editar = df_aop_para_editar.drop(columns=['FY'])
            df_aop_editado = st.data_editor(df_aop_para_editar, key=f"{planta_selecionada}_aop_{i}", use_container_width=True, num_rows="fixed", height=420)
            df_aop_editado = corrige_decimais_df(df_aop_editado).astype(float)

            # Tabela editável para o AOP (Meta) ou Ciclo Anterior (para override)
            st.markdown("##### 🧷 AOP ou Ciclo Anterior (Opcional)")
            # 'aop_show' é o que o usuário vê (pode ter dados mensais antigos + FY)
            df_aop_show_default = dados_salvos.get('aop_show', pd.DataFrame(index=kpis_da_planta, columns=MESES + ['FY']).fillna(0.0))
            # Garante que a coluna 'FY' (vinda do 'aop' salvo) esteja presente
            if 'FY' not in df_aop_show_default.columns:
                fy_values = dados_salvos_aop.get('FY', 0.0)
                df_aop_show_default['FY'] = fy_values
            df_aop_show_editado = st.data_editor(df_aop_show_default, key=f"{planta_selecionada}_aop_show_{i}", use_container_width=True, num_rows="fixed", height=420)
            df_aop_show_editado = corrige_decimais_df(df_aop_show_editado).astype(float)

            # Combina os dados das duas tabelas para salvar
            # 'aop' (dados reais YTD) + 'FY' (meta vinda da tabela 'aop_show')
            df_aop_final_para_salvar = df_aop_editado.copy()
            df_aop_final_para_salvar['FY'] = df_aop_show_editado['FY']

            # Salva os dados editados no estado da sessão
            plant_state['dados'][i] = {
                'volume': df_volume_editado.fillna(0.0),
                'aop': df_aop_final_para_salvar.fillna(0.0), # Dados reais YTD + Meta FY
                'aop_show': df_aop_show_editado.fillna(0.0) # Dados de AOP/Ciclo Antigo (para override)
            }
            set_plant_store(planta_selecionada, plant_state)
            # Adiciona aos dados que serão usados no cálculo
            dados_formatos[formato_atual] = plant_state['dados'][i]
            # --- FIM DA LÓGICA CORRIGIDA ---

    st.markdown("---")

    def is_spoilage(kpi_name: str) -> bool:
        """Helper para verificar se um KPI é 'Spoilage' (cálculo em %)."""
        return 'spoilage' in kpi_name.lower()

    # --- FUNÇÃO PRINCIPAL DE CÁLCULO ---
    def calc_kpi_por_formato(formato: str, df_vol: pd.DataFrame, df_aop: pd.DataFrame):
        """NÚCLEO DO CÁLCULO: Calcula o reforecast para UM formato."""
        vol_mensal = df_vol.loc['Volume Total'].astype(float).reindex(MESES).fillna(0.0)
        resultados_coef_anual = {} # Armazena o Coef. FY necessário
        metas_futuras = pd.DataFrame(0.0, index=df_aop.index, columns=MESES) # Armazena os coef. mensais futuros
        bloqueados = set() # Armazena KPIs que estouraram o AOP
        
        # Loop por cada KPI (linha) do formato
        for kpi in df_aop.index:
            serie = df_aop.loc[kpi].astype(float)
            serie_mes = serie.reindex(MESES).fillna(0.0) # Coeficientes mensais (YTD)
            fy = float(serie.get('FY', 0.0)) # Meta AOP (Coeficiente Anual)
            
            # Calcula o VALOR LÍQUIDO (Coef * Volume)
            if is_spoilage(kpi): # Spoilage é em % (divide por 100)
                realizado_ytd = ((serie_mes[colunas_ytd] / 100.0) * vol_mensal[colunas_ytd]).sum()
                total_fy = (fy / 100.0) * vol_mensal.sum()
            else: # Outros KPIs são diretos
                realizado_ytd = (serie_mes[colunas_ytd] * vol_mensal[colunas_ytd]).sum()
                total_fy = fy * vol_mensal.sum()
            
            EPS = 1e-9 # Epsilon para comparação de float
            if not np.isfinite(realizado_ytd): realizado_ytd = 0.0
            if not np.isfinite(total_fy): total_fy = 0.0
            
            # Lógica de BLOQUEIO: Se o YTD já estourou (ou empatou) a meta FY
            cond_excedeu = (total_fy > 0) and ((realizado_ytd > total_fy) or np.isclose(realizado_ytd, total_fy, rtol=0.0, atol=EPS))
            if cond_excedeu:
                bloqueados.add(kpi) # Adiciona KPI à lista de bloqueados
                resultados_coef_anual[kpi] = 0.0 # Meta futura é 0
                metas_futuras.loc[kpi, :] = 0.0 # Meta futura é 0
                st.warning(f"🔔 O KPI **{kpi}** do formato **{formato}** ultrapassou seu limite de saldo líquido.")
                continue # Pula para o próximo KPI
            
            # Calcula o SALDO LÍQUIDO restante para os meses futuros
            saldo_restante = max(total_fy - realizado_ytd, 0.0)
            # Calcula o VOLUME total a ser produzido nos meses futuros
            vol_fut = vol_mensal[colunas_futuro].sum()

            # Se não há volume futuro ou saldo, a meta futura é 0
            if vol_fut <= 0.0 or saldo_restante <= 0.0:
                resultados_coef_anual[kpi] = 0.0
                metas_futuras.loc[kpi, colunas_futuro] = 0.0
                continue
            
            # --- LÓGICA DE RATEIO DO SALDO ---
            # Calcula o valor líquido estimado para os meses futuros (usando coeficientes antigos)
            if is_spoilage(kpi):
                estimado_mes = (serie_mes[colunas_futuro] / 100.0) * vol_mensal[colunas_futuro]
            else:
                estimado_mes = (serie_mes[colunas_futuro]) * vol_mensal[colunas_futuro]
            total_estimado = float(estimado_mes.sum())
            
            # Se não há estimativa (coeficientes futuros antigos eram 0)
            if total_estimado <= 0.0:
                # Rateia o saldo restante proporcionalmente ao VOLUME futuro
                base_prop = vol_mensal[colunas_futuro]
                total_base = base_prop.sum()
                if total_base <= 0.0:
                    metas_coef = pd.Series(0.0, index=colunas_futuro)
                else:
                    proporcao = base_prop / total_base
                    metas_valor = proporcao * saldo_restante # Valor líquido distribuído
                    # Converte de volta para COEFICIENTE (Valor / Volume)
                    if is_spoilage(kpi):
                        metas_coef = (metas_valor / vol_mensal[colunas_futuro]).replace([np.inf, -np.inf], 0.0).fillna(0.0) * 100.0
                    else:
                        metas_coef = (metas_valor / vol_mensal[colunas_futuro]).replace([np.inf, -np.inf], 0.0).fillna(0.0)
                # Atribui os coeficientes calculados para os meses futuros
                metas_futuras.loc[kpi, colunas_futuro] = metas_coef.values
            else:
                # Rateia o saldo restante proporcionalmente à ESTIMATIVA futura
                proporcao = (estimado_mes / total_estimado).fillna(0.0)
                metas_valor = proporcao * saldo_restante # Valor líquido distribuído
                # Converte de volta para COEFICIENTE (Valor / Volume)
                if is_spoilage(kpi):
                    metas_coef = (metas_valor / vol_mensal[colunas_futuro]).replace([np.inf, -np.inf], 0.0).fillna(0.0) * 100.0
                else:
                    metas_coef = (metas_valor / vol_mensal[colunas_futuro]).replace([np.inf, -np.inf], 0.0).fillna(0.0)
                # Atribui os coeficientes calculados para os meses futuros
                metas_futuras.loc[kpi, colunas_futuro] = metas_coef.values
            
            # Calcula o COEFICIENTE MÉDIO (FY) necessário para o resto do ano
            if is_spoilage(kpi):
                resultados_coef_anual[kpi] = (saldo_restante / vol_fut) * 100.0 if vol_fut > 0 else 0.0
            else:
                resultados_coef_anual[kpi] = saldo_restante / vol_fut if vol_fut > 0 else 0.0
        
        # Retorna os resultados do cálculo para este formato
        return {'bloqueado_por_kpi': bloqueados, 'coef_anual_necessario': pd.Series(resultados_coef_anual), 'metas_futuras': metas_futuras}

    def mult_gas_df(df: pd.DataFrame, fator: float) -> pd.DataFrame:
        """Multiplica a linha de Gás (se existir) no DF pelo fator de conversão."""
        if GAS_KPI_NAME in df.index and fator != 1.0:
            df = df.copy()
            df.loc[GAS_KPI_NAME] = df.loc[GAS_KPI_NAME] * fator
        return df

    def mult_gas_series_as_row(series: pd.Series, fator: float) -> pd.DataFrame:
        """Converte uma Série, multiplica o Gás e retorna como DF (para tabelas de 1 linha)."""
        df = pd.DataFrame(series).T # Converte a Série para um DF de 1 linha
        if GAS_KPI_NAME in df.columns and fator != 1.0:
            df = df.copy()
            df[GAS_KPI_NAME] = df[GAS_KPI_NAME] * fator
        return df

    # --- SEÇÃO 5: CÁLCULO E RESULTADOS ---
    st.header("5️⃣ Cálculo e Resultados")
    # Inicia o cálculo ao clicar no botão
    if st.button("🚀 Calcular Reforecast", type="primary", use_container_width=True, key=f"{planta_selecionada}_calc"):
        # Mostra um indicador de carregamento
        with st.spinner("Consolidando dados e executando cálculos..."):
            # Define a ordem de exibição dos KPIs (Cans ou Ends)
            final_kpi_order = KPIS_CANS if PLANTAS_CONFIG[planta_selecionada]['tipo'] == 'Cans' else KPIS_ENDS
            
            # Coleta todos os dados de entrada dos formatos
            nomes_formatos = plant_state['nomes_formatos']
            volumes = {f: dados_formatos[f]['volume'] for f in nomes_formatos}
            aops = {f: dados_formatos[f]['aop'] for f in nomes_formatos} # (YTD Real + FY Meta)
            aops_show = {f: dados_formatos[f]['aop_show'] for f in nomes_formatos} # (AOP/Ciclo Antigo)
            
            resultados_por_formato = {}
            bloqueios_por_kpi = {k: set() for k in kpis_da_planta}
            
            # Executa o cálculo principal (calc_kpi_por_formato) para cada formato
            for formato in nomes_formatos:
                res = calc_kpi_por_formato(formato, volumes[formato], aops[formato])
                resultados_por_formato[formato] = res
                # Registra quais KPIs estouraram e em qual formato
                for kpi in res['bloqueado_por_kpi']:
                    bloqueios_por_kpi[kpi].add(formato)

            # Consolida KPIs que estouraram em *qualquer* formato
            kpis_bloqueados_no_geral = {k for k, fset in bloqueios_por_kpi.items() if len(fset) > 0}
            if len(kpis_bloqueados_no_geral) > 0:
                st.info("ℹ️ Para os KPIs com estouro em algum formato, o consolidado **Geral** foi suprimido para esses KPIs.")

            metas_finais_por_formato = {}
            avisos_por_formato = {}
            overrides_por_formato = {}  # << NOVO: marca linhas (KPIs) que repetiram o AOP

            # --- PÓS-PROCESSAMENTO (LÓGICA DE OVERRIDE) ---
            # Loop para aplicar overrides (lógica de "melhor performance")
            for formato in nomes_formatos:
                res = resultados_por_formato[formato]
                df_aop_formato = aops[formato] # (YTD Real + FY Meta)
                df_aop_show_formato = aops_show[formato] # (AOP/Ciclo Antigo)
                metas_a_exibir = res['metas_futuras'].copy() # Pega o resultado do cálculo
                avisos_performance = []
                overridden_kpis = set()  # << NOVO (KPIs que serão pintados de verde)

                for kpi in kpis_da_planta:
                    # Compara o Coef. FY (calculado) vs Coef. FY (meta AOP)
                    coef_calculado = res['coef_anual_necessario'].get(kpi, 0.0)
                    coef_fy_meta = df_aop_formato.loc[kpi, 'FY']
                    
                    # Lógica de OVERRIDE: Se o calculado > meta (melhor performance que o AOP)
                    if coef_fy_meta > 0 and coef_calculado > coef_fy_meta:
                        # Pega os valores da tabela "AOP ou Ciclo Anterior" (df_aop_show)
                        override_values = df_aop_show_formato.loc[kpi, colunas_futuro]
                        if override_values.sum() > 0: # Se houver dados lá
                            avisos_performance.append(
                                f"💡 KPI **{kpi}** teve performance melhor que o AOP. Exibindo valores de 'AOP ou Ciclo Anterior'."
                            )
                            # Substitui o valor calculado pelo valor do AOP/Ciclo Anterior
                            metas_a_exibir.loc[kpi, colunas_futuro] = override_values
                            overridden_kpis.add(kpi)  # << NOVO: Marca o KPI para pintar de verde

                metas_finais_por_formato[formato] = metas_a_exibir
                avisos_por_formato[formato] = avisos_performance
                overrides_por_formato[formato] = overridden_kpis  # << NOVO

            # --- EXIBIÇÃO DOS RESULTADOS ---
            # Cria as abas de resultado ('Geral' + cada formato)
            tab_labels = ['Geral'] + nomes_formatos
            abas = st.tabs(tab_labels)

            # --- ABA GERAL ---
            with abas[0]: # Lógica da aba "Geral"
                st.subheader("Resultado Geral")

                # --- CASO 1: Apenas 1 formato ---
                # Se só há 1 formato, "Geral" é igual ao resultado desse formato
                if len(nomes_formatos) == 1:
                    formato_unico = nomes_formatos[0]
                    chips_meses(colunas_ytd, colunas_futuro)
                    # Exibe os avisos de override (performance melhor)
                    if avisos_por_formato[formato_unico]:
                        st.write("")
                        for aviso in avisos_por_formato[formato_unico]:
                            st.info(aviso)
                        st.write("")
                    res_unico = resultados_por_formato[formato_unico]
                    
                    # Prepara a tabela de Valor Anual (FY)
                    df_anual_row_fmt = mult_gas_series_as_row(res_unico['coef_anual_necessario'], fator_gas) # Converte Gás
                    df_anual_row_fmt.index = ["Necessário (FY)"]
                    df_anual_renamed = renomear_gas_para_output(df_anual_row_fmt) # Renomeia Gás
                    df_anual_agregado = agregar_energia(df_anual_renamed, final_kpi_order) # Agrega Energia
                    st.markdown(f"**📊 Valor Anual**")
                    # Exibe a tabela de Valor Anual (FY) formatada (vermelho nos zeros)
                    st.dataframe(df_anual_agregado.style.applymap(highlight_zero).format(formatter="{:.3f}"))

                    # Prepara a tabela de Metas Futuras
                    metas_finais = metas_finais_por_formato[formato_unico]
                    metas_fmt_out = mult_gas_df(metas_finais, fator_gas) # Converte Gás
                    metas_renamed = renomear_gas_para_output(metas_fmt_out) # Renomeia Gás
                    metas_agregadas = agregar_energia(metas_renamed, final_kpi_order) # Agrega Energia
                    st.markdown(f"**📅 Metas Mensais Futuras**")
                    overrides_set = overrides_por_formato[formato_unico]
                    # Exibe a tabela de Metas Futuras (com estilo complexo: verde/vermelho)
                    styled = metas_agregadas[colunas_futuro].style.apply(
                        style_metas_with_overrides, overridden_set=overrides_set, axis=None
                    ).format(formatter="{:.3f}")
                    st.dataframe(styled)

                # --- CASO 2: Múltiplos formatos (Consolidação) ---
                else:
                    chips_meses(colunas_ytd, colunas_futuro)
                    # Soma o volume de todos os formatos
                    vol_total_df = pd.concat([volumes[f] for f in nomes_formatos]).groupby(level=0).sum()
                    
                    # Calcula o YTD e FY consolidados (somando valores líquidos)
                    realizado_ytd_total = pd.Series(0.0, index=kpis_da_planta)
                    total_fy_total = pd.Series(0.0, index=kpis_da_planta)
                    for kpi in kpis_da_planta:
                        for formato in nomes_formatos:
                            # Ignora formatos onde o KPI estourou
                            if formato in bloqueios_por_kpi.get(kpi, set()): continue
                            vol_formato = volumes[formato].loc['Volume Total']
                            aop_formato = aops[formato].loc[kpi]
                            # Soma os valores LÍQUIDOS (Coef * Vol)
                            if is_spoilage(kpi):
                                realizado_ytd_total[kpi] += ((aop_formato[colunas_ytd] / 100.0) * vol_formato[colunas_ytd]).sum()
                                total_fy_total[kpi] += (aop_formato['FY'] / 100.0) * vol_formato.sum()
                            else:
                                realizado_ytd_total[kpi] += (aop_formato[colunas_ytd] * vol_formato[colunas_ytd]).sum()
                                total_fy_total[kpi] += aop_formato['FY'] * vol_formato.sum()
                    
                    # Calcula o saldo e volume futuros consolidados
                    saldo_restante = (total_fy_total - realizado_ytd_total).clip(lower=0)
                    vol_fut_total = vol_total_df.loc['Volume Total', colunas_futuro].sum()
                    
                    # Calcula o coeficiente FY consolidado (ponderado)
                    geral_coef_anual = pd.Series(0.0, index=kpis_da_planta)
                    if vol_fut_total > 0:
                        for kpi in kpis_da_planta:
                            # Zera o KPI se ele estourou em algum formato
                            if kpi in kpis_bloqueados_no_geral: 
                                geral_coef_anual[kpi] = 0.0
                                continue
                            # Converte de Saldo Líquido para Coeficiente (Saldo / Volume Futuro)
                            if is_spoilage(kpi):
                                geral_coef_anual[kpi] = (saldo_restante[kpi] / vol_fut_total) * 100.0
                            else:
                                geral_coef_anual[kpi] = saldo_restante[kpi] / vol_fut_total
                    
                    # Prepara e exibe a tabela de Valor Anual (FY) Consolidado
                    df_anual_row_geral = mult_gas_series_as_row(geral_coef_anual, fator_gas)
                    df_anual_row_geral.index = ["Necessário (FY)"]
          D           df_anual_geral_renamed = renomear_gas_para_output(df_anual_row_geral)
                    df_anual_geral_agregado = agregar_energia(df_anual_geral_renamed, final_kpi_order)
                    st.markdown("**📊 Valor Anual (Consolidado)**")
                    st.dataframe(df_anual_geral_agregado.style.applymap(highlight_zero).format(formatter="{:.3f}"))
                    
                    # --- Cálculo das Metas Mensais Consolidadas ---
                    # Soma o volume futuro total por mês
                    volumes_producao_futuros_total_por_mes = pd.Series(0.0, index=colunas_futuro)
                    for formato in nomes_formatos:
                        volumes_producao_futuros_total_por_mes += volumes[formato].loc['Volume Total', colunas_futuro]
                    
                    geral_metas = pd.DataFrame(0.0, index=kpis_da_planta, columns=MESES)
                    # Suprime avisos de divisão por zero (caso o volume futuro do mês seja 0)
                    with np.errstate(divide='ignore', invalid='ignore'):
                        for kpi in kpis_da_planta:
                            # Zera o KPI se ele estourou em algum formato
                            if kpi in kpis_bloqueados_no_geral: 
                                geral_metas.loc[kpi, colunas_futuro] = 0.0
                                continue
                            
                            # Soma o valor líquido (coef * vol) de cada formato por mês
                            soma_liquido_kpi_por_mes = pd.Series(0.0, index=colunas_futuro)
                            for formato in nomes_formatos:
                                if formato in bloqueios_por_kpi.get(kpi, set()): continue
                                metas_futuras_formato = resultados_por_formato[formato]['metas_futuras']
                                volume_futuro_formato = volumes[formato].loc['Volume Total', colunas_futuro]
                                coeficientes_futuros = metas_futuras_formato.loc[kpi, colunas_futuro]
                                
                                # Calcula o valor líquido mensal daquele formato
                                if is_spoilage(kpi):
                                    valor_liquido_mensal = (coeficientes_futuros / 100.0) * volume_futuro_formato
                                else:
                                    valor_liquido_mensal = coeficientes_futuros * volume_futuro_formato
                                soma_liquido_kpi_por_mes += valor_liquido_mensal
                            
                            # Calcula o coeficiente médio ponderado consolidado por mês
                            # (Soma dos Líquidos / Soma dos Volumes)
                            coef_mensal = soma_liquido_kpi_por_mes / volumes_producao_futuros_total_por_mes
                            if is_spoilage(kpi):
                                geral_metas.loc[kpi, colunas_futuro] = coef_mensal.fillna(0.0) * 100.0
                            else:
                                geral_metas.loc[kpi, colunas_futuro] = coef_mensal.fillna(0.0)
                    
                    # Prepara e exibe a tabela de Metas Futuras Consolidadas
                    geral_metas_out = mult_gas_df(geral_metas, fator_gas)
                    geral_metas_renamed = renomear_gas_para_output(geral_metas_out)
                    geral_metas_agregadas = agregar_energia(geral_metas_renamed, final_kpi_order)
                    st.markdown("**📅 Metas Mensais Futuras (Consolidado)**")
                    # Consolidação não pinta verde (overrides são por formato), usa o estilo básico (só vermelho)
                    styled_cons = geral_metas_agregadas[colunas_futuro].style.apply(style_metas_basic, axis=None).format("{:.3f}")
                    st.dataframe(styled_cons)
            
            # --- ABAS POR FORMATO ---
            # Loop para criar o conteúdo das abas de cada formato individual
            for pos, formato in enumerate(nomes_formatos, start=1):
                with abas[pos]: # Lógica da aba de resultado por formato
                    st.subheader(f"Formato: {formato}")
                    chips_meses(colunas_ytd, colunas_futuro)
                    
                    # Exibe avisos de override (performance melhor)
                    avisos = avisos_por_formato[formato]
                    if avisos:
                        st.write("")
                        for aviso in avisos:
                            st.info(aviso)
                        st.write("")
                    
                    # Prepara e exibe o Valor Anual (FY) do formato
                    res_formato = resultados_por_formato[formato]
                    df_anual_row_fmt = mult_gas_series_as_row(res_formato['coef_anual_necessario'], fator_gas)
                    df_anual_row_fmt.index = ["Necessário (FY)"]
                    df_anual_formato_renamed = renomear_gas_para_output(df_anual_row_fmt)
                    df_anual_formato_agregado = agregar_energia(df_anual_formato_renamed, final_kpi_order)
                    st.markdown(f"**📊 Valor Anual ({formato})**")
                    st.dataframe(df_anual_formato_agregado.style.applymap(highlight_zero).format(formatter="{:.3f}"))
                    
                    # Prepara e exibe as Metas Mensais Futuras do formato
                    metas_finais = metas_finais_por_formato[formato]
                    metas_fmt_out = mult_gas_df(metas_finais, fator_gas)
                    metas_formato_renamed = renomear_gas_para_output(metas_fmt_out)
                    metas_formato_agregadas = agregar_energia(metas_formato_renamed, final_kpi_order)
                    st.markdown(f"**📅 Metas Mensais Futuras ({formato})**")
                    overrides_set_f = overrides_por_formato[formato]
                    # Aplica o estilo complexo (verde/vermelho) nos resultados do formato
                    styled_fmt = metas_formato_agregadas[colunas_futuro].style.apply(
                        style_metas_with_overrides, overridden_set=overrides_set_f, axis=None
                    ).format(formatter="{:.3f}")
                    st.dataframe(styled_fmt)

            # Mensagem de sucesso no final
            st.success("✅ Cálculos concluídos com sucesso!")

    # --- RODAPÉ ---
    st.markdown("---")
    st.markdown(f"<div style='text-align: center; color: gray;'>Calculadora Reforecast v12.7 | {datetime.now().year}</div>", unsafe_allow_html=True)

# Padrão de execução do script Python (inicia a função main)
if __name__ == "__main__":
    main()
