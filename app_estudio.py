import streamlit as st
import pandas as pd
import calendar
from datetime import date, timedelta, datetime

st.set_page_config(page_title="Planificador de Estudio", layout="wide")
st.title("📚 Planificador de estudio")

# --- PANEL LATERAL ---
with st.sidebar:
    st.header("1. Cargar progreso (Opcional)")
    st.info("Sube tu archivo .csv actualizado para recalcular el calendario.")
    archivo_progreso = st.file_uploader("Archivo de seguimiento", type=["csv"])
    
    st.header("2. Parámetros del Alumno")
    
    modo_seleccion = st.radio("¿Cómo prefieres indicar los temas?", ["Elegir temas concretos", "Por cantidad de temas"])
    
    if modo_seleccion == "Elegir temas concretos":
        lista_completa = list(range(1, 75))
        temas_seleccionados = st.multiselect(
            "Selecciona los temas a estudiar:", 
            options=lista_completa, 
            default=[1, 2, 3, 4, 5] 
        )
        st.info(f"Total a estudiar: {len(temas_seleccionados)} temas")
    else:
        cantidad = st.number_input("Número de temas para la prueba:", min_value=1, max_value=74, value=40)
        temas_seleccionados = list(range(1, cantidad + 1))
        st.info(f"Se planificarán los temas del 1 al {cantidad}.")
        
    num_temas = len(temas_seleccionados)

    fecha_inicio = st.date_input("Fecha de inicio (o recalcular desde)", value=date.today())
    fecha_fin = st.date_input("Fecha límite", value=date(2027, 6, 1))
    
    st.markdown("---")
    st.subheader("3. Disponibilidad Semanal")
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    tabla_turnos = pd.DataFrame({
        "Día": dias_semana,
        "Mañana": [True, True, True, True, True, False, False],
        "Tarde": [True, True, True, True, True, False, False]
    })
    turnos_elegidos = st.data_editor(tabla_turnos, hide_index=True, use_container_width=True)
    
    st.markdown("---")
    st.subheader("4. Días Libres o Festivos")
    st.info("Escribe las fechas en las que NO vas a estudiar, separadas por comas (Ej: 25/12/2026, 01/01/2027)")
    fechas_excluidas_input = st.text_input("Fechas a excluir (DD/MM/AAAA):", placeholder="25/12/2026, 01/01/2027")
    
    st.markdown("---")
    generar = st.button("Generar / Recalcular Calendario", type="primary")

# --- ALGORITMO PRINCIPAL ---
if generar:
    if num_temas == 0:
        st.error("⚠️ Debes seleccionar al menos un tema.")
        st.stop()

    fechas_excluidas = []
    if fechas_excluidas_input:
        for f in fechas_excluidas_input.split(','):
            try:
                fechas_excluidas.append(datetime.strptime(f.strip(), "%d/%m/%Y").date())
            except:
                pass 

    # A) PROCESAR EL ARCHIVO SUBIDO
    tareas_completadas = {}
    if archivo_progreso is not None:
        try:
            df_prog = pd.read_csv(archivo_progreso, sep=';')
            df_prog = df_prog[df_prog['Completado'].notna()] 
            for index, row in df_prog.iterrows():
                fecha_str = str(row['Fecha'])
                try:
                    f_obj = datetime.strptime(fecha_str, "%d/%m/%Y").date()
                except:
                    f_obj = fecha_inicio
                tareas_completadas[row['Tarea']] = f_obj
            st.success(f"📂 Archivo cargado: Se han detectado {len(tareas_completadas)} sesiones ya completadas.")
        except Exception as e:
            st.error("Error al leer el archivo. Asegúrate de que es el .csv original y está separado por punto y coma.")

    # B) EXTRAER HUECOS REALES FUTUROS
    huecos = []
    fecha_actual = fecha_inicio
    while fecha_actual <= fecha_fin:
        if fecha_actual not in fechas_excluidas:
            dia_idx = fecha_actual.weekday()
            if turnos_elegidos.iloc[dia_idx]['Mañana']:
                huecos.append({'fecha': fecha_actual, 'turno': 'Mañana', 'tarea': None})
            if turnos_elegidos.iloc[dia_idx]['Tarde']:
                huecos.append({'fecha': fecha_actual, 'turno': 'Tarde', 'tarea': None})
        fecha_actual += timedelta(days=1)
        
    turnos_totales = len(huecos)
    turnos_necesarios = (num_temas * 5) - len(tareas_completadas)
    
    # C) VALIDACIÓN DE VIABILIDAD
    if turnos_totales < turnos_necesarios:
        deficit = turnos_necesarios - turnos_totales
        if deficit <= num_temas:
            st.warning(f"⚠️ Ajustado: Faltan {deficit} turnos. Se generará el calendario pero algunos simulacros quedarán fuera.")
        else:
            st.error(f"❌ Inviable: Tienes {turnos_totales} turnos libres y necesitas {turnos_necesarios} para acabar. Amplía la fecha o reduce temas.")
            st.stop()
    else:
        st.success(f"✅ ¡Planificación viable! Tienes {turnos_totales} turnos libres para encajar las {turnos_necesarios} sesiones restantes.")

    # D) MOTOR DE ASIGNACIÓN INTELIGENTE
    fases_olvido = [('Preparación', 0), ('Estudio', 0), ('Repaso 1', 1), ('Repaso 2', 7), ('Simulacro', 15)]
    tareas_para_csv = []

    for t_str, f_obj in tareas_completadas.items():
        tareas_para_csv.append({'Fecha': f_obj.strftime("%d/%m/%Y"), 'Turno': '---', 'Tarea': t_str, 'Completado': 'Sí'})

    for tema in temas_seleccionados:
        fecha_base = None
        for nombre_fase, gap_dias in fases_olvido:
            tarea_str = f"T{tema} - {nombre_fase}"
            
            if tarea_str in tareas_completadas:
                fecha_base = tareas_completadas[tarea_str] 
            else:
                if fecha_base is None:
                    fecha_min = fecha_inicio
                else:
                    fecha_min = max(fecha_inicio, fecha_base + timedelta(days=gap_dias))

                for hueco in huecos:
                    if hueco['tarea'] is None and hueco['fecha'] >= fecha_min:
                        hueco['tarea'] = tarea_str
                        fecha_base = hueco['fecha']
                        tareas_para_csv.append({'Fecha': hueco['fecha'].strftime("%d/%m/%Y"), 'Turno': hueco['turno'], 'Tarea': tarea_str, 'Completado': None})
                        break

    # E) PREPARACIÓN DE VISUALES
    task_lookup = {}
    for h in huecos:
        d_key = h['fecha']
        if d_key not in task_lookup:
            task_lookup[d_key] = {"Mañana": "Libre", "Tarde": "Libre"}
        if h['tarea'] is not None:
            task_lookup[d_key][h['turno']] = h['tarea']

    meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    
    html_cal = """
    <style>
    .cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 5px; margin-bottom: 40px;}
    .cal-header { font-weight: bold; text-align: center; background-color: #f0f2f6; padding: 8px; border-radius: 5px;}
    .cal-day { border: 1px solid #e0e0e0; border-radius: 5px; padding: 5px; min-height: 110px; display: flex; flex-direction: column; background-color: white;}
    .cal-date { font-weight: bold; font-size: 14px; text-align: right; border-bottom: 1px solid #eee; margin-bottom: 5px; padding-bottom: 2px; color: #333;}
    .cal-m { background-color: #e8f4f8; font-size: 11px; padding: 4px; margin-bottom: 4px; border-radius: 3px; flex: 1; color: #0d47a1;}
    .cal-t { background-color: #fdf5e6; font-size: 11px; padding: 4px; border-radius: 3px; flex: 1; color: #e65100;}
    .cal-empty { background-color: #f8f9fa; border: 1px dashed #ddd; }
    .cal-festivo { background-color: #ffebee; border: 1px solid #ffcdd2; }
    .cal-title { font-family: sans-serif; color: #333; border-bottom: 2px solid #333; padding-bottom: 5px;}
    </style>
    """

    fechas_rango = [fecha_inicio + timedelta(days=x) for x in range((fecha_fin - fecha_inicio).days + 1)]
    if fechas_rango:
        meses_unicos = sorted(list(set((d.year, d.month) for d in fechas_rango)))
        for year, month in meses_unicos:
            html_cal += f"<h2 class='cal-title'>{meses_nombres[month-1]} {year}</h2><div class='cal-grid'>"
            for d in ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]:
                html_cal += f'<div class="cal-header">{d}</div>'
            cal_matrix = calendar.monthcalendar(year, month)
            for week in cal_matrix:
                for day in week:
                    if day == 0:
                        html_cal += '<div class="cal-day cal-empty"></div>'
                    else:
                        d_obj = date(year, month, day)
                        if d_obj < fecha_inicio or d_obj > fecha_fin:
                            html_cal += f'<div class="cal-day cal-empty"><div class="cal-date" style="color:#aaa;">{day}</div></div>'
                        elif d_obj in fechas_excluidas:
                            html_cal += f'<div class="cal-day cal-festivo"><div class="cal-date" style="color:#d32f2f;">{day}</div><div style="text-align:center; margin-top:20px; color:#d32f2f; font-size:12px;">🌴 Festivo</div></div>'
                        else:
                            t_man = task_lookup.get(d_obj, {}).get("Mañana", "Libre")
                            t_tar = task_lookup.get(d_obj, {}).get("Tarde", "Libre")
                            op_m = "opacity: 0.4;" if t_man == "Libre" else ""
                            op_t = "opacity: 0.4;" if t_tar == "Libre" else ""
                            t_man_html = f'<div class="cal-m" style="{op_m}">☀️ {t_man}</div>'
                            t_tar_html = f'<div class="cal-t" style="{op_t}">🌙 {t_tar}</div>'
                            html_cal += f'<div class="cal-day"><div class="cal-date">{day}</div>{t_man_html}{t_tar_html}</div>'
            html_cal += '</div>'

    # F) CÁLCULO DE ARCHIVOS DE DESCARGA
    html_export = f"<html><head><meta charset='utf-8'><title>Calendario Estudio</title>{html_cal}</head><body style='font-family: sans-serif; padding: 20px;' onload='window.print()'><h1>Planificación de Estudio</h1>{html_cal}</body></html>"
    
    df_export = pd.DataFrame(tareas_para_csv)
    df_export['Fecha_dt'] = pd.to_datetime(df_export['Fecha'], format="%d/%m/%Y")
    df_export = df_export.sort_values('Fecha_dt').drop(columns=['Fecha_dt'])
    csv_data = df_export.to_csv(index=False, sep=';').encode('utf-8-sig') 
    
    # NUEVO: Generador .ics limpio, a prueba de fallos para Google Calendar
    now_stamp = datetime.now().strftime("%Y%m%dT%H%M%SZ")
    lineas_ical = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Planificador Estudio//ES",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH"
    ]
    
    for idx, row in df_export.iterrows():
        if row['Turno'] == '---': continue 
        if row['Turno'] == 'Mañana':
            t_start, t_end = "090000", "130000"
        else:
            t_start, t_end = "160000", "200000"
            
        d_parts = row['Fecha'].split('/')
        d_str = f"{d_parts[2]}{d_parts[1]}{d_parts[0]}"
        
        # Identificador 100% libre de tildes y caracteres especiales
        uid = f"evento-{idx}-{d_str}-{t_start}@planificador"
        
        lineas_ical.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_stamp}",
            f"DTSTART:{d_str}T{t_start}",
            f"DTEND:{d_str}T{t_end}",
            f"SUMMARY:📚 {row['Tarea']}",
            f"DESCRIPTION:Turno de {row['Turno']}",
            "END:VEVENT"
        ])
        
    lineas_ical.append("END:VCALENDAR")
    # Los archivos ics requieren estrictamente saltos de línea con \r\n
    ical_content = "\r\n".join(lineas_ical) + "\r\n"

    # G) RENDERIZADO VISUAL
    st.markdown("### Exportar Planificación")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button("📥 PDF (Imprimir)", data=html_export, file_name="calendario_estudio.html", mime="text/html", use_container_width=True)
    with col2:
        st.download_button("📊 Excel (.csv)", data=csv_data, file_name="seguimiento_estudio.csv", mime="text/csv", use_container_width=True)
    with col3:
        st.download_button("📅 Google Calendar (.ics)", data=ical_content.encode('utf-8'), file_name="calendario_estudio.ics", mime="text/calendar", use_container_width=True)
        
    st.markdown("---")
    st.markdown("### Calendario Visual")
    st.markdown(html_cal, unsafe_allow_html=True)
