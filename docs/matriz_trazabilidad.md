# Matriz de trazabilidad - Cluster F40

| CP | Tecnica | Requisito | Descripcion | Prueba | Resultado |
|----|---------|-----------|-------------|--------|-----------|
| CA-01 | Aceptacion (dirigida por datos) | R01 | velocimetro: estado seguro, ciclo de 100 ms, limite 360 km/h y regreso a 0 al apagar (R01). | `test_aceptacion.py::test_ca01_velocimetro` | PASS |
| CA-02 | Aceptacion (dirigida por datos) | R01 | medidor 2 ambar bajo 1 bar con motor activo, cruzando el umbral en ambos sentidos (R01). | `test_aceptacion.py::test_ca02_presion_aceite` | PASS |
| CA-03 | Aceptacion (dirigida por datos) | R01, R03 | tacometro rojo en 8000, histeresis hasta 7799 y RPM a 0 al apagar (R01, R03). | `test_aceptacion.py::test_ca03_tacometro` | PASS |
| CA-04 | Aceptacion (dirigida por datos) | R04 | temperatura roja sobre 110, histeresis hasta 105 y ciclo de 500 ms (R04). | `test_aceptacion.py::test_ca04_temperatura_agua` | PASS |
| CA-05 | Aceptacion (dirigida por datos) | R05 | contorno ambar sobre 1.5 bar e histeresis hasta 1.4 bar (R05). | `test_aceptacion.py::test_ca05_presion_turbo` | PASS |
| CA-06 | Aceptacion (dirigida por datos) | R06 | testigo 6 verde alternando cada 500 ms con IZQ y DER, apagado con OFF (R06). | `test_aceptacion.py::test_ca06_direccionales` | PASS |
| CA-07 | Aceptacion (dirigida por datos) | R01, R07 | testigo 7 azul fijo con motor encendido y apagado con motor apagado (R01, R07). | `test_aceptacion.py::test_ca07_luces_altas` | PASS |
| CA-08 | Aceptacion (dirigida por datos) | R06, R07 | testigo 8 ambar alternando cada 500 ms con precedencia visual sobre el 6 (R06, R07). | `test_aceptacion.py::test_ca08_emergencia_y_precedencia` | PASS |
| CA-09 | Aceptacion (dirigida por datos) | R01, R02 | testigo 9 rojo tras 1 s bajo 1 bar y apagado tras 1 s en 1.2 bar (R01, R02). | `test_aceptacion.py::test_ca09_baja_presion_aceite` | PASS |
| CA-10 | Aceptacion (dirigida por datos) | R01, R08 | testigo 10 rojo alternando cada 300 ms aun con motor apagado (R01, R08). | `test_aceptacion.py::test_ca10_falla_frenos` | PASS |
| CP-01 | Particion de equivalencia | - | velocidad dentro de 0-360 se aplica tras su ciclo (100 ms). | `test_particiones.py::test_cp01_velocidad_valida_se_aplica` | PASS |
| CP-02 | Particion de equivalencia | R03 | rpm entero dentro de 0-9000 se aplica tras su ciclo (100 ms). [R03] | `test_particiones.py::test_cp02_rpm_valido_se_aplica` | PASS |
| CP-03 | Particion de equivalencia | R02 | presion de aceite dentro de 0-10 se aplica tras su ciclo (100 ms). [R02] | `test_particiones.py::test_cp03_presion_aceite_valida_se_aplica` | PASS |
| CP-04 | Particion de equivalencia | R04 | temperatura de agua dentro de 40-130 se aplica tras su ciclo (500 ms). [R04] | `test_particiones.py::test_cp04_temp_agua_valida_se_aplica` | PASS |
| CP-05 | Particion de equivalencia | R05 | presion de turbo dentro de 0-2 se aplica tras su ciclo (100 ms). [R05] | `test_particiones.py::test_cp05_presion_turbo_valida_se_aplica` | PASS |
| CP-06 | Particion de equivalencia | R06 | direccional IZQ es un valor valido. [R06] | `test_particiones.py::test_cp06_direccional_izq_valida` | PASS |
| CP-07 | Particion de equivalencia | R06 | direccional DER es un valor valido. [R06] | `test_particiones.py::test_cp07_direccional_der_valida` | PASS |
| CP-08 | Particion de equivalencia | R06 | direccional OFF es un valor valido (estado seguro). [R06] | `test_particiones.py::test_cp08_direccional_off_valida` | PASS |
| CP-09 | Particion de equivalencia | R07, R08 | los interruptores aceptan True/False. [R07, R08] | `test_particiones.py::test_cp09_interruptores_booleanos_validos` | PASS |
| CP-10 | Particion de equivalencia | - | 0 km/h es parte de la particion valida. | `test_particiones.py::test_cp10_velocidad_cero_particion_valida` | PASS |
| CP-11 | Valores limite | - | 0 km/h es el limite inferior valido. | `test_limites.py::test_cp11_velocidad_limite_inferior_0` | PASS |
| CP-12 | Valores limite | - | 360 km/h es el limite superior valido. | `test_limites.py::test_cp12_velocidad_limite_superior_360` | PASS |
| CP-13 | Valores limite | R03 | 7799 rpm no activa rojo. [R03] | `test_limites.py::test_cp13_rpm_7799_no_activa_rojo` | PASS |
| CP-14 | Valores limite | R03 | 7800 rpm (zona muerta) conserva el estado previo (normal). [R03] | `test_limites.py::test_cp14_rpm_7800_zona_muerta_conserva_normal` | PASS |
| CP-15 | Valores limite | R03 | en zona muerta (7999) se conserva el estado previo, partiendo de rojo. [R03] | `test_limites.py::test_cp15_rpm_7999_conserva_rojo_si_ya_estaba_rojo` | PASS |
| CP-16 | Valores limite | R03 | 8000 rpm activa el indicador rojo (R03). | `test_limites.py::test_cp16_rpm_8000_activa_rojo` | PASS |
| CP-17 | Valores limite | R02 | 0.99 bar sostenido 999 ms NO activa el testigo 9 todavia. [R02] | `test_limites.py::test_cp17_aceite_099_bar_999ms_no_activa_testigo` | PASS |
| CP-18 | Valores limite | R02 | 0.99 bar sostenido >= 1000 ms SI activa el testigo 9 (R02). | `test_limites.py::test_cp18_aceite_099_bar_1000ms_activa_testigo` | PASS |
| CP-19 | Valores limite | R02 | 1.0 bar esta en zona muerta: no activa el testigo aunque pase tiempo. [R02] | `test_limites.py::test_cp19_aceite_10_bar_zona_muerta_no_activa` | PASS |
| CP-20 | Valores limite | R02 | 1.2 bar sostenido >= 1 s apaga el testigo 9 (histeresis, R02). | `test_limites.py::test_cp20_aceite_12_bar_1000ms_apaga_testigo` | PASS |
| CP-21 | Valores limite | R04 | 105 C: limite donde regresa a normal. [R04] | `test_limites.py::test_cp21_temp_105_normal` | PASS |
| CP-22 | Valores limite | R04 | 110 C esta en zona muerta: conserva estado previo (normal). [R04] | `test_limites.py::test_cp22_temp_110_zona_muerta_conserva_previo` | PASS |
| CP-23 | Valores limite | R04 | 110.1 C activa el indicador rojo (R04). | `test_limites.py::test_cp23_temp_1101_activa_rojo` | PASS |
| CP-24 | Valores limite | R05 | 1.4 bar: limite donde el contorno regresa a normal. [R05] | `test_limites.py::test_cp24_turbo_14_normal` | PASS |
| CP-25 | Valores limite | R05 | 1.5 bar esta en zona muerta: conserva estado previo (normal). [R05] | `test_limites.py::test_cp25_turbo_15_zona_muerta_conserva_previo` | PASS |
| CP-26 | Valores limite | R05 | 1.51 bar activa el contorno ambar (R05). | `test_limites.py::test_cp26_turbo_151_activa_ambar` | PASS |
| CP-27 | Transicion de estados | R03 | el indicador de rpm sube a rojo en 8000 y baja a normal en 7799. [R03] | `test_transiciones.py::test_cp27_rpm_histeresis_sube_y_baja` | PASS |
| CP-28 | Transicion de estados | R04 | histeresis de temperatura de agua (R04). | `test_transiciones.py::test_cp28_temp_histeresis_sube_y_baja` | PASS |
| CP-29 | Transicion de estados | R05 | histeresis de presion de turbo (R05). | `test_transiciones.py::test_cp29_turbo_histeresis_sube_y_baja` | PASS |
| CP-30 | Transicion de estados | R06 | el testigo de direccional alterna cada 500 ms (R06). | `test_transiciones.py::test_cp30_parpadeo_direccional_500ms` | PASS |
| CP-31 | Transicion de estados | R07 | el testigo de emergencia alterna cada 500 ms (R07). | `test_transiciones.py::test_cp31_parpadeo_emergencia_500ms` | PASS |
| CP-32 | Transicion de estados | R08 | el testigo de falla de frenos alterna cada 300 ms (R08). | `test_transiciones.py::test_cp32_parpadeo_frenos_300ms` | PASS |
| CP-33 | Transicion de estados | R07 | con direccional puesto y emergencia activa, hay precedencia visual (R07). | `test_transiciones.py::test_cp33_emergencia_tiene_precedencia_sobre_direccional` | PASS |
| CP-34 | Transicion de estados | R07 | sin emergencia activa, no hay precedencia aunque haya direccional. [R07] | `test_transiciones.py::test_cp34_sin_emergencia_no_hay_precedencia` | PASS |
| CP-35 | Transicion de estados | R01 | al encender el motor, las lecturas empiezan a actualizarse segun su ciclo. [R01] | `test_transiciones.py::test_cp35_encender_motor_desde_apagado` | PASS |
| CP-36 | Transicion de estados | R01 | al apagar el motor, todas las lecturas vuelven de inmediato a su valor seguro. [R01] | `test_transiciones.py::test_cp36_apagar_motor_fuerza_valores_seguros` | PASS |
| CP-37 | Transicion de estados | R01, R02 | al apagar el motor se apaga el testigo 9 y se reinicia su temporizador. [R01, R02] | `test_transiciones.py::test_cp37_apagar_motor_apaga_testigo_aceite` | PASS |
| CP-38 | Entradas invalidas | - | velocidad negativa es invalida (ValueError). | `test_invalidas.py::test_cp38_velocidad_fuera_rango_negativa` | PASS |
| CP-39 | Entradas invalidas | - | velocidad > 360 es invalida (ValueError). | `test_invalidas.py::test_cp39_velocidad_fuera_rango_superior` | PASS |
| CP-40 | Entradas invalidas | R03 | rpm debe ser entero; un float se rechaza con TypeError. [R03] | `test_invalidas.py::test_cp40_rpm_tipo_float_invalido` | PASS |
| CP-41 | Entradas invalidas | R03 | rpm no acepta bool. [R03] | `test_invalidas.py::test_cp41_rpm_tipo_bool_invalido` | PASS |
| CP-42 | Entradas invalidas | R03 | rpm > 9000 es invalido (ValueError). [R03] | `test_invalidas.py::test_cp42_rpm_fuera_rango` | PASS |
| CP-43 | Entradas invalidas | R02 | presion de aceite > 10 es invalida (ValueError). [R02] | `test_invalidas.py::test_cp43_presion_aceite_fuera_rango` | PASS |
| CP-44 | Entradas invalidas | R02 | presion de aceite no acepta str (TypeError). [R02] | `test_invalidas.py::test_cp44_presion_aceite_tipo_invalido` | PASS |
| CP-45 | Entradas invalidas | R04 | temperatura < 40 es invalida (ValueError). [R04] | `test_invalidas.py::test_cp45_temp_agua_fuera_rango_inferior` | PASS |
| CP-46 | Entradas invalidas | R04 | temperatura > 130 es invalida (ValueError). [R04] | `test_invalidas.py::test_cp46_temp_agua_fuera_rango_superior` | PASS |
| CP-47 | Entradas invalidas | R05 | presion de turbo > 2 es invalida (ValueError). [R05] | `test_invalidas.py::test_cp47_presion_turbo_fuera_rango` | PASS |
| CP-48 | Entradas invalidas | R05 | presion de turbo no acepta bool (TypeError). [R05] | `test_invalidas.py::test_cp48_presion_turbo_bool_invalido` | PASS |
| CP-49 | Entradas invalidas | R06 | un direccional fuera de OFF/IZQ/DER es invalido (ValueError). [R06] | `test_invalidas.py::test_cp49_direccional_desconocido` | PASS |
| CP-50 | Entradas invalidas | R06 | direccional debe ser str; un entero se rechaza (TypeError). [R06] | `test_invalidas.py::test_cp50_direccional_tipo_invalido` | PASS |
| CP-51 | Entradas invalidas | R01 | motor debe ser bool; un int se rechaza (TypeError). [R01] | `test_invalidas.py::test_cp51_motor_tipo_invalido` | PASS |
| CP-52 | Entradas invalidas | - | una entrada rechazada no modifica el objetivo previo. | `test_invalidas.py::test_cp52_entrada_rechazada_no_cambia_estado` | PASS |
| CP-53 | Caja blanca (cobertura) | R01 | motor_activo refleja el ultimo valor de set_motor. [R01] | `test_complementarias.py::test_cp53_motor_activo_refleja_set_motor` | PASS |
| CP-54 | Caja blanca (cobertura) | R01 | con el motor apagado el elemento 2 siempre es normal. [R01] | `test_complementarias.py::test_cp54_color_aceite_motor_apagado_normal` | PASS |
| CP-55 | Caja blanca (cobertura) | - | p_aceite < 1 bar pone el elemento 2 en ambar sin esperar 1 s. | `test_complementarias.py::test_cp55_color_aceite_bajo_1_bar_ambar_inmediato` | PASS |
| CP-56 | Caja blanca (cobertura) | - | p_aceite = 1.0 bar deja el elemento 2 en normal. | `test_complementarias.py::test_cp56_color_aceite_1_bar_normal` | PASS |
| CP-57 | Caja blanca (cobertura) | R06 | con direccional OFF y motor encendido el testigo 6 nunca enciende (R06). | `test_complementarias.py::test_cp57_direccional_off_no_parpadea` | PASS |
| CP-58 | Caja blanca (cobertura) | R07 | con emergencia desactivada y motor encendido el testigo 8 nunca enciende (R07). | `test_complementarias.py::test_cp58_emergencia_desactivada_no_parpadea` | PASS |
| CP-59 | Caja blanca (cobertura) | R08 | sin falla de frenos el testigo nunca enciende (R08). | `test_complementarias.py::test_cp59_falla_frenos_desactivada_no_parpadea` | PASS |
| CP-60 | Caja blanca (cobertura) | - | RelojReal arranca cerca de 0 ms y es monotono. | `test_complementarias.py::test_cp60_reloj_real_arranca_en_cero_y_no_retrocede` | PASS |
| CP-61 | Caja blanca (cobertura) | - | avanzar() rechaza str, None y bool con TypeError. | `test_complementarias.py::test_cp61_reloj_simulado_rechaza_tipo_invalido` | PASS |
| CP-62 | Caja blanca (cobertura) | - | avanzar() rechaza milisegundos negativos con ValueError. | `test_complementarias.py::test_cp62_reloj_simulado_rechaza_negativo` | PASS |
| CP-63 | Caja blanca (cobertura) | - | avanzar() acumula y devuelve el total (int y float). | `test_complementarias.py::test_cp63_reloj_simulado_acumula` | PASS |
| CP-64 | Basada en requisitos | R07 | con motor encendido las luces altas quedan fijas, sin parpadeo (R07). | `test_requisitos.py::test_cp64_luces_altas_fijas_sin_parpadeo` | PASS |
| CP-65 | Basada en requisitos | R01, R07 | con el motor apagado el testigo de luces altas no enciende (R01, R07). | `test_requisitos.py::test_cp65_luces_altas_apagadas_con_motor_apagado` | PASS |
| CP-66 | Basada en requisitos | R01, R08 | el testigo 10 (critico) parpadea cada 300 ms aunque el motor este apagado y se apaga con falla_frenos=0 (R01, R08). | `test_requisitos.py::test_cp66_frenos_parpadea_aun_con_motor_apagado` | PASS |
| CP-67 | Presentacion (caja negra) | - | la vista expone los 10 elementos con la numeracion y categorias oficiales. | `test_presentacion.py::test_cp67_diez_elementos_con_numeracion_y_categoria` | PASS |
| CP-68 | Presentacion (caja negra) | R01 | al iniciar, agujas en su minimo, colores normales y testigos apagados (R01). | `test_presentacion.py::test_cp68_estado_inicial_seguro` | PASS |
| CP-69 | Presentacion (caja negra) | R03, R04, R05 | 2 ambar (<1 bar), 3 rojo (>=8000), 4 rojo (>110), 5 ambar (>1.5) (R03, R04, R05). | `test_presentacion.py::test_cp69_colores_de_advertencia_de_lecturas` | PASS |
| CP-70 | Presentacion (caja negra) | R02 | el medidor 2 cambia a ambar de inmediato y el testigo 9 solo tras 1 s (R02). | `test_presentacion.py::test_cp70_testigo_9_distinto_del_medidor_2` | PASS |
| CP-71 | Presentacion (caja negra) | R06, R07 | con emergencia activa el testigo 6 no se dibuja y el 8 si; sin ella, el 6 vuelve (R06, R07). | `test_presentacion.py::test_cp71_emergencia_tiene_precedencia_visual_sobre_giro` | PASS |
| CP-72 | Presentacion (caja negra) | R07, R08 | el testigo 7 se dibuja azul y el 10 rojo (R07, R08). | `test_presentacion.py::test_cp72_luces_altas_azul_y_frenos_rojo` | PASS |
| CP-73 | Presentacion (caja negra) | R01 | la aguja se ubica en proporcion al rango (180 km/h = mitad, 9000 RPM = tope) (R01). | `test_presentacion.py::test_cp73_posicion_de_aguja_proporcional` | PASS |
| CP-74 | Integracion UI (Tkinter) | R01 | los controles inician en estado seguro y los testigos se dibujan apagados (R01). | `test_tablero.py::test_cp74_ventana_arranca_en_estado_seguro` | PASS |
| CP-75 | Integracion UI (Tkinter) | R03 | encender el motor y llevar RPM a 8000 dibuja el tacometro en rojo (R03). | `test_tablero.py::test_cp75_mover_controles_actualiza_el_dibujo` | PASS |
| CP-76 | Integracion UI (Tkinter) | R08 | 9 y 10 son rectangulos con borde rojo; 6-8 son circulos; el 10 se enciende rojo (R08). | `test_tablero.py::test_cp76_testigos_criticos_visualmente_distintos` | PASS |
| CP-77 | Integracion UI (Tkinter) | - | un valor invalido muestra un mensaje en pantalla y no modifica el estado. | `test_tablero.py::test_cp77_entrada_rechazada_se_informa_y_no_cambia_estado` | PASS |
| CP-78 | Integracion UI (Tkinter) | - | main.py abre la aplicacion con el reloj real y se cierra sola (prueba de humo). | `test_tablero.py::test_cp78_main_arranca_y_cierra` | PASS |
| CP-79 | Aceptacion (dirigida por datos) | - | un archivo de escenarios inexistente se informa con un error claro. | `test_aceptacion.py::test_cp79_archivo_inexistente` | PASS |
| CP-80 | Aceptacion (dirigida por datos) | - | un archivo vacio o solo con cabecera se rechaza. | `test_aceptacion.py::test_cp80_archivo_vacio_o_sin_pasos` | PASS |
| CP-81 | Aceptacion (dirigida por datos) | - | si falta una columna obligatoria se informa cual. | `test_aceptacion.py::test_cp81_columna_faltante` | PASS |
| CP-82 | Aceptacion (dirigida por datos) | - | un control que no existe se rechaza indicando la linea. | `test_aceptacion.py::test_cp82_control_desconocido` | PASS |
| CP-83 | Aceptacion (dirigida por datos) | - | un valor no numerico para un deslizador se rechaza. | `test_aceptacion.py::test_cp83_valor_no_numerico` | PASS |
| CP-84 | Aceptacion (dirigida por datos) | - | filas con esperado, elemento, tiempo, numero de paso o valor invalidos se rechazan. | `test_aceptacion.py::test_cp84_filas_invalidas` | PASS |
| CP-85 | Aceptacion (dirigida por datos) | - | el CSV de aceptacion define CA-01 a CA-10 y recorre los 10 controles. | `test_aceptacion.py::test_cp85_archivo_real_cubre_10_escenarios_y_todos_los_controles` | PASS |
| CP-86 | Integracion UI (Tkinter) | - | detener el refresco dos veces no produce error (cierre seguro de la ventana). | `test_tablero.py::test_cp86_detener_dos_veces_no_falla` | PASS |
| CP-87 | Aceptacion (dirigida por datos) | - | el ejecutor de aceptacion sin archivo muestra el uso y devuelve 2. | `test_aceptacion.py::test_cp87_main_sin_argumentos` | PASS |
| CP-88 | Aceptacion (dirigida por datos) | - | el ejecutor con un archivo inexistente muestra ERROR y devuelve 2. | `test_aceptacion.py::test_cp88_main_archivo_inexistente` | PASS |
| CP-89 | Aceptacion (dirigida por datos) | - | el ejecutor con el CSV real aprueba los 10 escenarios y devuelve 0. | `test_aceptacion.py::test_cp89_main_con_archivo_real` | PASS |
| CP-90 | Aceptacion (dirigida por datos) | - | el oraculo detecta una diferencia: una expectativa falsa da FALLIDO y devuelve 1. | `test_aceptacion.py::test_cp90_main_detecta_expectativa_incorrecta` | PASS |

## Resumen

- Casos de prueba: 100
- Pasaron: 100
- Fallo esperado por defecto abierto (XFAIL): 0
- Fallaron / otros: 0

## Casos por requisito

| Requisito | Casos |
|-----------|-------|
| R01 | CA-01, CA-02, CA-03, CA-07, CA-09, CA-10, CP-35, CP-36, CP-37, CP-51, CP-53, CP-54, CP-65, CP-66, CP-68, CP-73, CP-74 |
| R02 | CA-09, CP-03, CP-17, CP-18, CP-19, CP-20, CP-37, CP-43, CP-44, CP-70 |
| R03 | CA-03, CP-02, CP-13, CP-14, CP-15, CP-16, CP-27, CP-40, CP-41, CP-42, CP-69, CP-75 |
| R04 | CA-04, CP-04, CP-21, CP-22, CP-23, CP-28, CP-45, CP-46, CP-69 |
| R05 | CA-05, CP-05, CP-24, CP-25, CP-26, CP-29, CP-47, CP-48, CP-69 |
| R06 | CA-06, CA-08, CP-06, CP-07, CP-08, CP-30, CP-49, CP-50, CP-57, CP-71 |
| R07 | CA-07, CA-08, CP-09, CP-31, CP-33, CP-34, CP-58, CP-64, CP-65, CP-71, CP-72 |
| R08 | CA-10, CP-09, CP-32, CP-59, CP-66, CP-72, CP-76 |

Requisitos sin casos: ninguno
