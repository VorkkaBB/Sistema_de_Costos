import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="Sistema de Costos - Final", layout="wide")

# MÓDULO 1: FUNCIONES DE ALMACÉN

def calcular_promedio(movimientos):
    filas = []
    saldo_unidades = 0; saldo_dinero = 0
    for mov in movimientos:
        tipo = mov['tipo']; cantidad = mov['cantidad']; costo_input = mov['costo_unitario']; fecha = mov['fecha']
        entrada_u = entrada_c = entrada_t = 0; salida_u = salida_c = salida_t = 0
        
        if tipo in ['Inventario Inicial', 'Compra']:
            entrada_u = cantidad; entrada_c = costo_input; entrada_t = cantidad * costo_input
            saldo_unidades += entrada_u; saldo_dinero += entrada_t
        elif tipo == 'Venta/Consumo':
            costo_salida = (saldo_dinero / saldo_unidades) if saldo_unidades > 0 else 0
            salida_u = cantidad; salida_c = costo_salida; salida_t = cantidad * costo_salida
            saldo_unidades -= salida_u; saldo_dinero -= salida_t
            
        costo_prom = (saldo_dinero / saldo_unidades) if saldo_unidades > 0 else 0
        filas.append([fecha, tipo, entrada_u, entrada_c, entrada_t, salida_u, salida_c, salida_t, saldo_unidades, costo_prom, saldo_dinero])
    return filas

def calcular_peps_ueps(movimientos, metodo='PEPS'):
    filas = []; capas = []; saldo_unidades = 0; saldo_dinero = 0
    for mov in movimientos:
        tipo = mov['tipo']; cantidad = mov['cantidad']; costo_input = mov['costo_unitario']; fecha = mov['fecha']
        entrada_u = entrada_c = entrada_t = 0; salida_u = salida_c = salida_t = 0

        if tipo in ['Inventario Inicial', 'Compra']:
            capas.append([cantidad, costo_input])
            entrada_u = cantidad; entrada_c = costo_input; entrada_t = cantidad * costo_input
            saldo_unidades += entrada_u; saldo_dinero += entrada_t
        elif tipo == 'Venta/Consumo':
            por_sacar = cantidad; costo_acum_salida = 0
            while por_sacar > 0 and capas:
                idx = 0 if metodo == 'PEPS' else -1
                capa = capas[idx]
                if capa[0] > por_sacar:
                    costo_acum_salida += por_sacar * capa[1]; capa[0] -= por_sacar; por_sacar = 0
                else:
                    costo_acum_salida += capa[0] * capa[1]; por_sacar -= capa[0]; capas.pop(idx)
            salida_u = cantidad; salida_c = costo_acum_salida/cantidad if cantidad>0 else 0; salida_t = costo_acum_salida
            saldo_unidades -= salida_u; saldo_dinero -= salida_t
            
        costo_saldo = saldo_dinero / saldo_unidades if saldo_unidades > 0 else 0
        filas.append([fecha, tipo, entrada_u, entrada_c, entrada_t, salida_u, salida_c, salida_t, saldo_unidades, costo_saldo, saldo_dinero])
    return filas

# INTERFAZ PRINCIPAL

def main():
    st.sidebar.title("Menú Principal")
    modulo = st.sidebar.radio("Selecciona:", ["Tarjetas de Almacén", "Calculadora de Prorrateos"])

    # MÓDULO 1: ALMACÉN

    if modulo == "Tarjetas de Almacén":
        st.title("📦 Tarjetas de Almacén")
        if 'movimientos' not in st.session_state: st.session_state['movimientos'] = []

        with st.expander("📝 Registrar Movimiento", expanded=True):
            c1, c2, c3, c4 = st.columns(4)
            fecha = c1.date_input("Fecha", value=date.today())
            tipo = c2.selectbox("Concepto", ["Inventario Inicial", "Compra", "Venta/Consumo"])
            cant = c3.number_input("Unidades", min_value=1, value=10)
            costo = c4.number_input("Costo Unitario ($)", min_value=0.0, value=100.0) if tipo != "Venta/Consumo" else 0.0
            
            if st.button("Agregar Movimiento"):
                stock = sum([m['cantidad'] if m['tipo']!='Venta/Consumo' else -m['cantidad'] for m in st.session_state['movimientos']])
                if tipo == 'Venta/Consumo' and cant > stock: st.error(f"Stock insuficiente ({stock}).")
                else: 
                    st.session_state['movimientos'].append({"fecha": fecha, "tipo": tipo, "cantidad": cant, "costo_unitario": costo})
                    st.success("Agregado")

        st.divider()
        if len(st.session_state['movimientos']) > 0:
            metodo = st.radio("Método:", ["Promedio", "PEPS", "UEPS"], horizontal=True)
            datos = calcular_promedio(st.session_state['movimientos']) if metodo == "Promedio" else calcular_peps_ueps(st.session_state['movimientos'], metodo)
            
            cols = pd.MultiIndex.from_tuples([("Datos","Fecha"),("Datos","Concepto"),("Entradas","Unidades"),("Entradas","Costo U"),("Entradas","Total"),("Salidas","Unidades"),("Salidas","Costo U"),("Salidas","Total"),("Existencias","Unidades"),("Existencias","Costo U"),("Existencias","Total")])
            
            st.dataframe(pd.DataFrame(datos, columns=cols).style.format({
                ("Entradas", "Costo U"): "${:,.2f}", ("Entradas", "Total"): "${:,.2f}",
                ("Salidas", "Costo U"): "${:,.2f}", ("Salidas", "Total"): "${:,.2f}",
                ("Existencias", "Costo U"): "${:,.2f}", ("Existencias", "Total"): "${:,.2f}",
                ("Existencias", "Unidades"): "{:,.0f}"
            }), width='stretch')
            
            if st.button("Borrar Tarjeta"): st.session_state['movimientos'] = []; st.rerun()

    # MÓDULO 2: PRORRATEOS

    elif modulo == "Calculadora de Prorrateos":
        st.title("🏭 Calculadora de Prorrateos")

        # NOMBRES
        st.header("Configuración")
        c1, c2 = st.columns(2)
        n_p1 = c1.text_input("Productivo 1", value="A")
        n_p2 = c1.text_input("Productivo 2", value="B")
        n_s1 = c2.text_input("Servicio 1", value="C")
        n_s2 = c2.text_input("Servicio 2", value="D")
        cols_deptos = [n_p1, n_p2, n_s1, n_s2]

        # Inicializar tabla
        if 'df_prim' not in st.session_state: st.session_state['df_prim'] = pd.DataFrame(columns=["Concepto"] + cols_deptos)
        if list(st.session_state['df_prim'].columns) != ["Concepto"] + cols_deptos: st.session_state['df_prim'].columns = ["Concepto"] + cols_deptos

        # CÉDULA I
        st.divider(); st.header("Cédula I: Prorrateo Primario")

        # A) Manual
        st.markdown("#### A) Agregar M.P.I/M.O.I (Manual)")
        with st.container():
            c_i1, c_i2, c_i3, c_i4, c_i5 = st.columns(5)
            nom_man = c_i1.text_input("Concepto", value="M.P.I.")
            v1 = c_i2.number_input(f"{n_p1}", 0.0); v2 = c_i3.number_input(f"{n_p2}", 0.0)
            v3 = c_i4.number_input(f"{n_s1}", 0.0); v4 = c_i5.number_input(f"{n_s2}", 0.0)
            if st.button("➕ Agregar Fila a 📊 Tabla Cédula I"):
                st.session_state['df_prim'] = pd.concat([st.session_state['df_prim'], pd.DataFrame([[nom_man, v1, v2, v3, v4]], columns=["Concepto"]+cols_deptos)], ignore_index=True)
                st.rerun()

        # B) Calculadora
        st.markdown("#### B) Calculadora de C.I")
        with st.expander("🧮 Abrir Calculadora", expanded=False):
            cx1, cx2 = st.columns(2)
            g_nom = cx1.text_input("Gasto", value="Renta"); g_tot = cx2.number_input("Total ($)", 0.0)
            b1, b2, b3, b4 = st.columns(4)
            vb1 = b1.number_input(f"Base {n_p1}", key="cb1"); vb2 = b2.number_input(f"Base {n_p2}", key="cb2")
            vb3 = b3.number_input(f"Base {n_s1}", key="cb3"); vb4 = b4.number_input(f"Base {n_s2}", key="cb4")
            if st.button("Calcular y Agregar a 📊 Tabla Cédula I"):
                tb = vb1+vb2+vb3+vb4
                if tb > 0:
                    f = g_tot/tb
                    st.session_state['df_prim'] = pd.concat([st.session_state['df_prim'], pd.DataFrame([[g_nom, vb1*f, vb2*f, vb3*f, vb4*f]], columns=["Concepto"]+cols_deptos)], ignore_index=True)
                    st.rerun()

        # Tabla acumulada
        st.write("---")
        st.markdown("### 📊 Tabla Cédula I")
        if not st.session_state['df_prim'].empty:
            df_v = st.session_state['df_prim'].copy()
            df_v["TOTAL"] = df_v[cols_deptos].sum(axis=1)
            sum_c = df_v.drop(columns=["Concepto"]).sum(); sum_c["Concepto"] = "TOTALES"
            st.dataframe(pd.concat([df_v, pd.DataFrame([sum_c])], ignore_index=True).style.format("${:,.2f}", subset=cols_deptos+["TOTAL"]), width='stretch')
            tot_prim = sum_c
            if st.button("Limpiar Cédula I"): st.session_state['df_prim'] = pd.DataFrame(columns=["Concepto"] + cols_deptos); st.rerun()
        else:
            tot_prim = pd.Series([0,0,0,0], index=cols_deptos); st.info("Tabla vacía")

        # CÉDULA II
        st.divider(); st.header("Cédula II: Prorrateo Secundario")
        orden = st.radio("Orden:", [f"{n_s1} -> {n_s2}", f"{n_s2} -> {n_s1} (Orden)"], horizontal=True)
        primero, segundo = (n_s2, n_s1) if "Orden" in orden else (n_s1, n_s2)

        # REPARTO 1
        val_1 = tot_prim[primero] if not st.session_state['df_prim'].empty else 0
        st.subheader(f"A) Distribución de {primero} (A repartir: ${val_1:,.2f})")
        
        m1 = st.radio(f"{primero}:", ["Automático (Bases Directas)", "Manual (C.E)"], horizontal=True, key="m1")
        
        c1, c2, c3 = st.columns(3)
        b1_p1 = c1.number_input(f"Base {n_p1}", 0.0, key="s1"); b1_p2 = c2.number_input(f"Base {n_p2}", 0.0, key="s2"); b1_s = c3.number_input(f"Base {segundo}", 0.0, key="s3")
        
        if m1 == "Automático (Bases Directas)":
            tb1 = b1_p1+b1_p2+b1_s; fac1 = val_1/tb1 if tb1>0 else 0
            st.info(f"Factor: {val_1:,.2f} / {tb1} = **{fac1:,.4f}**")
        else:
            txt1 = st.text_input(f"Fórmula (ej. {val_1:.0f}/Total)", value="1/1", key="t1")
            try: num, den = txt1.split("/") if "/" in txt1 else (txt1, 1); fac1 = float(num)/float(den)
            except: fac1 = 0
            st.info(f"C.E: {fac1:,.4f}")
        
        asig1 = {n_p1: b1_p1*fac1, n_p2: b1_p2*fac1, segundo: b1_s*fac1}

        # REPARTO 2
        val_2 = (tot_prim[segundo] if not st.session_state['df_prim'].empty else 0) + asig1[segundo]
        st.divider(); st.subheader(f"B) Distribución de {segundo} (A repartir: ${val_2:,.2f})")
        
        m2 = st.radio(f"{segundo}:", ["Automático (Bases Directas)", "Manual (C.E)"], horizontal=True, key="m2")
        
        c4, c5 = st.columns(2)
        b2_p1 = c4.number_input(f"Base {n_p1}", 0.0, key="s4"); b2_p2 = c5.number_input(f"Base {n_p2}", 0.0, key="s5")
        
        if m2 == "Automático (Bases Directas)":
            tb2 = b2_p1+b2_p2; fac2 = val_2/tb2 if tb2>0 else 0
            st.info(f"Factor: {val_2:,.2f} / {tb2} = **{fac2:,.4f}**")
        else:
            txt2 = st.text_input(f"Fórmula (ej. {val_2:.0f}/Total)", value="1/1", key="t2")
            try: num, den = txt2.split("/") if "/" in txt2 else (txt2, 1); fac2 = float(num)/float(den)
            except: fac2 = 0
            st.info(f"C.E: {fac2:,.4f}")

        asig2 = {n_p1: b2_p1*fac2, n_p2: b2_p2*fac2}

        # Tabla II
        vp1 = tot_prim[n_p1] if not st.session_state['df_prim'].empty else 0
        vp2 = tot_prim[n_p2] if not st.session_state['df_prim'].empty else 0
        gp1 = vp1 + asig1[n_p1] + asig2[n_p1]; gp2 = vp2 + asig1[n_p2] + asig2[n_p2]

        st.markdown("### 📊 Tabla Cédula II")

        df_ced2 = pd.DataFrame([
            ["Total P.P", vp1, vp2, val_1, (tot_prim[segundo] if not st.session_state['df_prim'].empty else 0)],
            [f"De {primero}", asig1[n_p1], asig1[n_p2], -val_1, asig1[segundo]],
            [f"Subtotal", 0, 0, 0, val_2],
            [f"De {segundo}", asig2[n_p1], asig2[n_p2], 0, -val_2],
            ["TOTALES", gp1, gp2, 0, 0]
        ], columns=["Concepto", n_p1, n_p2, primero, segundo])
        df_ced2["TOTAL"] = df_ced2[cols_deptos].sum(axis=1)
        st.dataframe(df_ced2.style.format("${:,.2f}", subset=cols_deptos+["TOTAL"]), width='stretch')

        # CÉDULA III
        st.divider(); st.header("Cédula III: Prorrateo Final")
        col_orden = "Orden"; col_b1 = f"Base {n_p1}"; col_b2 = f"Base {n_p2}"; col_u = "Unidades"
        cols_fin = [col_orden, col_b1, col_b2, col_u]

        if 'df_final' not in st.session_state: 
            st.session_state['df_final'] = pd.DataFrame(columns=cols_fin)

        if list(st.session_state['df_final'].columns) != cols_fin:
             st.session_state['df_final'].columns = cols_fin

        with st.container():
            c_f1, c_f2, c_f3, c_f4, c_f5 = st.columns(5)
            no = c_f1.text_input("Orden", "Prod/Orden"); nb1 = c_f2.number_input(f"Base {n_p1}", 0.0); nb2 = c_f3.number_input(f"Base {n_p2}", 0.0); nu = c_f4.number_input("Unidades", 0.0)
            if c_f5.button("➕ Agregar"):
                st.session_state['df_final'] = pd.concat([st.session_state['df_final'], pd.DataFrame([[no, nb1, nb2, nu]], columns=cols_fin)], ignore_index=True)
                st.rerun()

        st.markdown("##### Factores Finales")
        col_fac1, col_fac2 = st.columns(2)
        
        with col_fac1:
            st.markdown(f"**Depto {n_p1}** (Total: ${gp1:,.2f})")
            met_f1 = st.radio("Método:", ["Automático", "Manual (C.E)"], key="mf1", horizontal=True)
            if met_f1 == "Automático":
                sb1 = st.session_state['df_final'][col_b1].sum(); ff1 = gp1/sb1 if sb1 > 0 else 0
                st.info(f"Calc: **{ff1:,.4f}**")
            else:
                tf1 = st.text_input(f"Fórmula {n_p1}", value=f"{gp1:.0f}/1", key="tff1")
                try: num, den = tf1.split("/") if "/" in tf1 else (tf1, 1); ff1 = float(num)/float(den)
                except: ff1 = 0
                st.info(f"C.E: **{ff1:,.4f}**")

        with col_fac2:
            st.markdown(f"**Depto {n_p2}** (Total: ${gp2:,.2f})")
            met_f2 = st.radio("Método:", ["Automático", "Manual (C.E)"], key="mf2", horizontal=True)
            if met_f2 == "Automático":
                sb2 = st.session_state['df_final'][col_b2].sum(); ff2 = gp2/sb2 if sb2 > 0 else 0
                st.info(f"Calc: **{ff2:,.4f}**")
            else:
                tf2 = st.text_input(f"Fórmula {n_p2}", value=f"{gp2:.0f}/1", key="tff2")
                try: num, den = tf2.split("/") if "/" in tf2 else (tf2, 1); ff2 = float(num)/float(den)
                except: ff2 = 0
                st.info(f"C.E: **{ff2:,.4f}**")

        if not st.session_state['df_final'].empty:
            df_res = st.session_state['df_final'].copy()
            df_res[f"Costo {n_p1}"] = df_res[col_b1] * ff1
            df_res[f"Costo {n_p2}"] = df_res[col_b2] * ff2
            df_res["TOTAL"] = df_res[f"Costo {n_p1}"] + df_res[f"Costo {n_p2}"]
            df_res["UNITARIO"] = df_res.apply(lambda x: x["TOTAL"]/x["Unidades"] if x["Unidades"]>0 else 0, axis=1)

            st.markdown("### 📊 Tabla Cédula III")
            
            sf = df_res.sum(numeric_only=True); sf["Orden"] = "SUMA TOTAL"
            
            formatos = {col_b1: "{:,.2f}", col_b2: "{:,.2f}", "Unidades": "{:,.0f}", f"Costo {n_p1}": "${:,.2f}", f"Costo {n_p2}": "${:,.2f}", "TOTAL": "${:,.2f}", "UNITARIO": "${:,.2f}"}
            st.dataframe(pd.concat([df_res, pd.DataFrame([sf])], ignore_index=True).style.format(formatos), width='stretch')
            
            if st.button("Limpiar Órdenes"): st.session_state['df_final'] = pd.DataFrame(columns=cols_fin); st.rerun()

    st.divider()
    if st.button("🗑️ Borrar Todo", type="primary"): st.session_state.clear(); st.rerun()

if __name__ == "__main__":
    main()