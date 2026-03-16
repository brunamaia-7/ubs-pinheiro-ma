import pandas as pd
import geopandas as gpd
import streamlit as st
import folium
from streamlit_folium import folium_static
from folium.plugins import MarkerCluster
import json
import traceback

# ================= CONFIGURAÇÃO =================
st.set_page_config(
    page_title="Análise de UBS - Pinheiro/MA",
    layout="wide",
    page_icon="🏥"
)

# ================= LEITURA DOS DADOS =================
@st.cache_data
def load_data():
    try:
        municipio = gpd.read_file("assets/pinheiro.json")
        ubs = gpd.read_file("assets/ubs_pinheiro.json")
        
        # Garante CRS correto
        municipio = municipio.to_crs(epsg=4326)
        ubs = ubs.to_crs(epsg=4326)
        
        return municipio, ubs
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {str(e)}")
        st.code(traceback.format_exc())
        return None, None

municipio, ubs = load_data()

# Verifica se os dados foram carregados
if municipio is None or ubs is None:
    municipio = gpd.read_file("./assets/assets/pinheiro.json")

# ================= DIAGNÓSTICO DOS DADOS =================
# ================= LOGOS NO PAINEL LATERAL =================
with st.sidebar:
    # Container para os logos
    logo_container = st.container()
    
    with logo_container:
        # Cria colunas para os logos
        col4, col5, col6 = st.columns([1, 1, 1])
        
        # Logo 1 - Use o caminho correto para suas imagens
        with col4:
            try:
                st.image("assets/logo_pet.png", 
                        caption="", 
                        width=110)
            except:
                st.image("https://via.placeholder.com/80x80/2E7D32/FFFFFF?text=Logo1", 
                        caption="Logo 1", 
                        width=110)
        
        # Logo 2
        with col5:
            try:
                st.image("assets/lageos.jpeg", 
                        caption="", 
                        width=110)
            except:
                st.image("https://via.placeholder.com/80x80/1565C0/FFFFFF?text=Logo2", 
                        caption="Logo 2", 
                        width=110)
        
        # Logo 3
        with col6:
            try:
                st.image("assets/brasao-normal.png", 
                        caption="", 
                        width=110)
            except:
                st.image("https://via.placeholder.com/80x80/D32F2F/FFFFFF?text=Logo3", 
                        caption="Logo 3", 
                        width=110)
    
    
    # Título abaixo dos logos
    st.markdown("### 🏥 Projeto de Informação e Saúde Digital")

    st.markdown("""PET-Saúde/I&SD – UFMA""")

# ================= IDENTIFICAÇÃO DO CAMPO NOME =================
def encontrar_campo_nome(gdf):
    """Encontra automaticamente o campo que contém os nomes das UBS"""
    
    # Lista de possíveis nomes de coluna (em ordem de prioridade)
    possiveis_nomes = [
        'UBS Coco', 'UBS Kiola Sarney', 'UBS Pacas', 'UBS São José', 'NAME',
        'ubs_nome', 'ubs_name', 'estabelecimento',
        'local', 'endereco', 'descricao', 'farmacia',
        'unidade', 'ponto', 'ponto_de_atendimento'
    ]
    
    # 1. Tenta encontrar por nome exato
    for nome in possiveis_nomes:
        if nome in gdf.columns:
            return nome
    
    # 2. Procura colunas de texto
    colunas_texto = gdf.select_dtypes(include=['object', 'string']).columns
    if len(colunas_texto) > 0:
        return colunas_texto[0]
    
    # 3. Procura qualquer coluna não-geométrica
    colunas_nao_geo = [col for col in gdf.columns if col != 'geometry']
    if len(colunas_nao_geo) > 0:
        return colunas_nao_geo[0]
    
    # 4. Último recurso: cria uma coluna numérica
    return "ID"

# Identifica o campo do nome
campo_nome = encontrar_campo_nome(ubs)

# Cria uma coluna de nome se não existir
if campo_nome == "ID":
    ubs["ID"] = [f"UBS {i+1}" for i in range(len(ubs))]

# ================= SIDEBAR PRINCIPAL =================
with st.sidebar:
    st.divider()
    
    tile = st.radio(
        "Mapa base",
        ["OpenStreetMap", "Satélite"],
        index=0
    )
    
    show_limites = st.checkbox("Mostrar limites municipais", True)
    cluster = st.checkbox("Agrupar UBS", True)
    zoom = st.slider("🔍 Nível de zoom", 10, 15, 11)

# ================= MAPA =================

# Calcula centro
try:
    centro = [
        float(municipio.geometry.centroid.y.mean()),
        float(municipio.geometry.centroid.x.mean())
    ]
except:
    # Fallback para centro aproximado de Pinheiro/MA
    centro = [-2.5213, -45.0825]

# Cria o mapa base com OpenStreetMap
m = folium.Map(
    location=centro,
    zoom_start=zoom,
    tiles="OpenStreetMap",
    attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    control_scale=True
)

# Se a opção selecionada for Satélite, adiciona a camada de satélite
if tile == "Satélite":
    # Adiciona camada de satélite
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr='Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
        name="Satélite",
        overlay=False,
        control=True
    ).add_to(m)

# Adiciona limites municipais
if show_limites and not municipio.empty:
    folium.GeoJson(
        municipio,
        style_function=lambda x: {
            'color': '#2E7D32',
            'weight': 2,
            'fillOpacity': 0.15,
            'fillColor': '#2E7D32'
        },
        name="Limite Municipal",
        tooltip="Município de Pinheiro/MA"
    ).add_to(m)

# Adiciona UBS
if not ubs.empty:
    # Verifica se deve usar cluster
    if cluster and len(ubs) > 1:
        marker_cluster = MarkerCluster(name="UBS").add_to(m)
        layer = marker_cluster
    else:
        layer = m
    
    # Adiciona marcadores
    for idx, row in ubs.iterrows():
        # Extrai coordenadas da geometria
        if hasattr(row.geometry, 'x') and hasattr(row.geometry, 'y'):
            lat, lon = row.geometry.y, row.geometry.x
        elif hasattr(row.geometry, 'centroid'):
            lat, lon = row.geometry.centroid.y, row.geometry.centroid.x
        else:
            continue  # Pula geometrias inválidas
        
        # Obtém o nome da UBS
        nome_ubs = str(row.get(campo_nome, f"UBS {idx+1}"))
        
        # Cria popup
        popup_content = f"<b>{nome_ubs}</b><br>"
        popup_content += f"Lat: {lat:.6f}<br>Lon: {lon:.6f}"
        
        # Adiciona outras informações disponíveis
        for col in ubs.columns:
            if col not in ['geometry', campo_nome] and pd.notna(row.get(col, None)):
                popup_content += f"<br><b>{col}:</b> {row[col]}"
        
        # Adiciona marcador
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_content, max_width=300),
            tooltip=nome_ubs,
            icon=folium.Icon(color="red", icon="plus-sign", prefix="glyphicon")
        ).add_to(layer)

# Adiciona controle de camadas
folium.LayerControl().add_to(m)

# ================= INTERFACE PRINCIPAL =================
st.title("📍 Distribuição Espacial das UBS – Pinheiro/MA")

# Container para o mapa sem espaçamento
with st.container():
    # CSS inline específico para este container
    st.markdown("""
    <style>
        div[data-testid="column"] {
            margin-top: -10px !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Mapa com altura ajustada e sem margens
        folium_static(m, height=520)  # Ajuste a altura conforme necessário
        
    
    with col2:
        # Estatísticas com layout mais compacto
        st.markdown("""
        <div style="margin-top: -15px;">
        """, unsafe_allow_html=True)
        
        st.subheader("📊 Estatísticas")
        st.metric("Total de UBS", len(ubs), label_visibility="visible")
        
        st.subheader("🏥 Lista de UBS")
        if not ubs.empty:
            # Lista mais compacta
            for idx, row in ubs.iterrows():
                nome = str(row.get(campo_nome, f"UBS {idx+1}"))
                st.markdown(f"<div style='margin: 2px 0;'>• {nome}</div>", 
                          unsafe_allow_html=True)
        else:
            st.info("Nenhuma UBS encontrada.")

# ================= TABELA DE DADOS =================
st.subheader("📋 Dados das UBS")

if not ubs.empty:
    # Prepara dados para exibição
    dados_exibicao = ubs.copy()
    
    # Adiciona coordenadas como colunas separadas
    dados_exibicao['latitude'] = dados_exibicao.geometry.apply(
        lambda geom: geom.y if hasattr(geom, 'y') else None
    )
    dados_exibicao['longitude'] = dados_exibicao.geometry.apply(
        lambda geom: geom.x if hasattr(geom, 'x') else None
    )
    
    # Remove a coluna geometry para exibição
    if 'geometry' in dados_exibicao.columns:
        dados_exibicao = dados_exibicao.drop(columns=['geometry'])
    
    # Exibe a tabela
    st.dataframe(dados_exibicao, use_container_width=True)
else:
    st.warning("Não há dados para exibir.")

# ================= EXPORTAÇÃO =================
st.divider()
st.subheader("📥 Exportar Dados")

if not ubs.empty and not municipio.empty:
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Exportar UBS como CSV (sem geometria)
        if 'geometry' in ubs.columns:
            ubs_sem_geom = ubs.drop(columns=['geometry'])
        else:
            ubs_sem_geom = ubs
        
        csv = ubs_sem_geom.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📊 Baixar UBS em CSV",
            data=csv,
            file_name="ubs_pinheiro.csv",
            mime="text/csv",
            help="Baixe os dados das UBS em formato CSV (Excel)"
        )
    
    with col2:
        # Exportar UBS como GeoJSON
        ubs_geojson = ubs.to_json()
        st.download_button(
            label="🗺️ Baixar UBS em GeoJSON",
            data=ubs_geojson,
            file_name="ubs_pinheiro.geojson",
            mime="application/json",
            help="Baixe os dados das UBS em formato GeoJSON (para SIG)"
        )
    
    with col3:
        # Exportar município como GeoJSON
        municipio_geojson = municipio.to_json()
        st.download_button(
            label="🗺️ Baixar Município GeoJSON",
            data=municipio_geojson,
            file_name="municipio_pinheiro.geojson",
            mime="application/json",
            help="Baixe o limite do município de Pinheiro em formato GeoJSON"
        )
else:
    st.info("Não há dados para exportar.")

# ================= RODAPÉ =================
st.divider()
st.markdown("""
<div style="text-align: center; font-size: 1em; padding: 20px;">
<hr style="border: none; height: 1px; background-color: #ddd; margin: 20px 0;">
<div style="text-align: left; margin: 20px;">

<b> Sistema:</b> Dashboard UBS – Pinheiro/MA<br>
<b> Projeto:</b> Programa de Educação pelo Trabalho para a Saúde: Informação e Saúde Digital (PET-Saúde/I&SD)<br>
<b> Tecnologias:</b> Python, Streamlit, GeoPandas, Folium<br>
<b> Base cartográfica:</b> OpenStreetMap<br>
<b> Finalidade:</b> Planejamento em Saúde Pública<br><br>

<b> Equipe:</b><br>
<div style="column-count: 2; column-gap: 40px; margin: 10px 0;">
• Anne Karine Martins Assunção da Silva<br>
• Adilson Matheus Borges Machado<br>
• Jonatas da Silva Castro<br>
• Alisson Freitas Santos Brandão da Silva<br>
• Luenne Sinara Ribeiro Pinheiro<br>
• Sônia Maria Silva Luz<br>
• Lindomar Christian da Trindade Filho<br>
• Cleiciane Cordeiro Coutinho<br>
• Nalleny Perpétua dos Santos Marinho<br>
• Cleyce Jane Costa Moraes<br>
• Alice Beatriz Tomaz Tavares<br>
• Enzo Marcos Costa Guterres<br>
• Lucas Gomes da Silva<br>
• Kauã de Assis Menezes Reis<br>
• Bruna Pereira Maia Silva<br>
• Geciane Pereira Aroucha<br>
</div><br>

<b> Desenvolvimento:</b> Adilson Matheus Borges Machado e Bruna Pereira Maia Silva<br><br>

<small>Município de Pinheiro/MA • Desenvolvido para pesquisa em saúde pública</small>
</div>
</div>
""", unsafe_allow_html=True)