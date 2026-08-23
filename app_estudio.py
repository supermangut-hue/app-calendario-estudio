import streamlit as st
import pandas as pd
import calendar
from datetime import date, timedelta

st.set_page_config(page_title="Calendario de Oposiciones", layout="wide")
st.title("📚 Calendario de estudio")

# --- PANEL LATERAL ---
with st.sidebar:
    st.header("Parámetros del Alumno")
    num_temas = st.number_input("Número de temas a estudiar", min_value=1, max_value=70, value=40)
    fecha_inicio = st.date_input("Fecha de inicio", value=date.today())
    fecha_fin = st.date_input("Fecha límite", value=date(2027, 6, 1))
    
    st.markdown("---")
    st.subheader("Disponibilidad Semanal")
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    tabla_turnos = pd.DataFrame({
        "Día": dias_semana,
        "Mañana": [True, True, True, True, True, False, False],
        "Tarde": [True, True, True, True, True, False, False]
    })
    
    turnos_elegidos = st.data_editor(tabla_turnos, hide_index=True, use_container_width=True)
    st.markdown("---")
    generar = st.button("Generar Calendario Completo", type="primary")

# --- ALGORITMO PRINCIPAL ---
if generar:
    # 1. Extraer huecos reales
    huecos = []
    fecha_actual = fecha_inicio
    while fecha_actual <= fecha_fin:
        dia_idx = fecha_actual.weekday()
        if turnos_elegidos.iloc[dia_idx]['Mañana']:
            huecos.append({'fecha': fecha_actual, 'turno': 'Mañana', 'tarea': None})
        if turnos_elegidos.iloc[dia_idx]['Tarde']:
            huecos.append({'fecha': fecha_actual, 'turno': 'Tarde', 'tarea': None})
        fecha_actual += timedelta(days=1)
        
    turnos_totales = len(huecos)
    turnos_necesarios = num_temas * 5
    
    # 2. Validación
    if turnos_totales < turnos_necesarios:
        deficit = turnos_necesarios - turnos_totales
        if deficit <= num_temas:
            st.warning(f"⚠️ Ajustado: Faltan {deficit} turnos. El calendario se generará, pero algunos simulacros quedarán fuera.")
        else:
            st.error(f"❌ Inviable: Tienes {turnos_totales} turnos pero necesitas {turnos_necesarios}. Amplía la fecha o reduce temas.")
            st.stop()
    else:
        st.success(f"✅ ¡Planificación perfecta! Tienes {turnos_totales} turnos para {turnos_necesarios} sesiones.")

    # 3. Asignación (Curva del Olvido)
    fases_olvido = [('Preparación', 0), ('Estudio', 0), ('Repaso 1', 1), ('Repaso 2', 7), ('Simulacro', 15)]
    
    for tema in range(1, num_temas + 1):
        fecha_minima_fase = fecha_inicio
        for nombre_fase, gap_dias in fases_olvido:
            fecha_minima_fase += timedelta(days=gap_dias)
            for hueco in huecos:
                if hueco['tarea'] is None and hueco['fecha'] >= fecha_minima_fase:
                    hueco['tarea'] = f"T{tema} - {nombre_fase}"
                    fecha_minima_fase = hueco['fecha']
                    break

    # 4. Construcción del Diccionario de Tareas por Día
    task_lookup = {}
    for h in huecos:
        d_key = h['fecha']
        if d_key not in task_lookup:
            task_lookup[d_key] = {"Mañana": "Libre", "Tarde": "Libre"}
        if h['tarea'] is not None:
            task_lookup[d_key][h['turno']] = h['tarea']

    # 5. RENDERIZADO VISUAL DEL CALENDARIO (HTML/CSS)
    meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    
    # Estilos CSS para la cuadrícula
    html_cal = """
    <style>
    .cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 5px; margin-bottom: 40px;}
    .cal-header { font-weight: bold; text-align: center; background-color: #f0f2f6; padding: 8px; border-radius: 5px;}
    .cal-day { border: 1px solid #e0e0e0; border-radius: 5px; padding: 5px; min-height: 110px; display: flex; flex-direction: column; background-color: white;}
    .cal-date { font-weight: bold; font-size: 14px; text-align: right; border-bottom: 1px solid #eee; margin-bottom: 5px; padding-bottom: 2px; color: #333;}
    .cal-m { background-color: #e8f4f8; font-size: 11px; padding: 4px; margin-bottom: 4px; border-radius: 3px; flex: 1; color: #0d47a1;}
    .cal-t { background-color: #fdf5e6; font-size: 11px; padding: 4px; border-radius: 3px; flex: 1; color: #e65100;}
    .cal-empty { background-color: #f8f9fa; border: 1px dashed #ddd; }
    .cal-title { font-family: sans-serif; color: #333; border-bottom: 2px solid #333; padding-bottom: 5px;}
    </style>
    """

    # Generamos la vista mes a mes
    fechas_rango = [fecha_inicio + timedelta(days=x) for x in range((fecha_fin - fecha_inicio).days + 1)]
    meses_unicos = sorted(list(set((d.year, d.month) for d in fechas_rango)))

    for year, month in meses_unicos:
        html_cal += f"<h2 class='cal-title'>{meses_nombres[month-1]} {year}</h2>"
        html_cal += '<div class="cal-grid">'
        # Cabecera de días
        for d in ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]:
            html_cal += f'<div class="cal-header">{d}</div>'

        # Matriz del mes
        cal_matrix = calendar.monthcalendar(year, month)
        for week in cal_matrix:
            for day in week:
                if day == 0:
                    html_cal += '<div class="cal-day cal-empty"></div>'
                else:
                    d_obj = date(year, month, day)
                    if d_obj < fecha_inicio or d_obj > fecha_fin:
                        html_cal += f'<div class="cal-day cal-empty"><div class="cal-date" style="color:#aaa;">{day}</div></div>'
                    else:
                        t_man = task_lookup.get(d_obj, {}).get("Mañana", "Libre")
                        t_tar = task_lookup.get(d_obj, {}).get("Tarde", "Libre")
                        
                        op_m = "opacity: 0.4;" if t_man == "Libre" else ""
                        op_t = "opacity: 0.4;" if t_tar == "Libre" else ""

                        t_man_html = f'<div class="cal-m" style="{op_m}">☀️ {t_man}</div>'
                        t_tar_html = f'<div class="cal-t" style="{op_t}">🌙 {t_tar}</div>'

                        html_cal += f'<div class="cal-day"><div class="cal-date">{day}</div>{t_man_html}{t_tar_html}</div>'
        html_cal += '</div>'

    # 6. Mostrar en la web
    st.markdown(html_cal, unsafe_allow_html=True)
    
    # 7. Botón para exportar a PDF (mediante impresión del navegador)
    html_export = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>Calendario Estudio</title>
        {html_cal}
    </head>
    <body style="font-family: sans-serif; padding: 20px;" onload="window.print()">
        <h1>Planificación de Estudio</h1>
        {html_cal}
    </body>
    </html>
    """
    
    st.download_button(
        label="📥 Descargar Calendario para PDF",
        data=html_export,
        file_name="calendario_estudio.html",
        mime="text/html",
        help="Abre el archivo descargado y se abrirá la opción para guardarlo como PDF."
    )
