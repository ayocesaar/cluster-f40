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
| CP-91 | Sistema (archivos, bitacoras, concurrencia) | R01 | P01 un valor valido del archivo actualiza el indicador y deja un evento INFO (R01). | `test_sistema.py::test_cp91_p01_valor_normal_actualiza_y_registra_info` | PASS |
| CP-92 | Sistema (archivos, bitacoras, concurrencia) | R01, R02, R03, R04, R05 | P02 los valores minimos permitidos se aceptan sin error (R01, R02, R03, R04, R05). | `test_sistema.py::test_cp92_p02_limites_inferiores_aceptados` | PASS |
| CP-93 | Sistema (archivos, bitacoras, concurrencia) | R01, R02, R03, R04, R05 | P03 los valores maximos permitidos se aceptan sin error (R01, R02, R03, R04, R05). | `test_sistema.py::test_cp93_p03_limites_superiores_aceptados` | PASS |
| CP-94 | Sistema (archivos, bitacoras, concurrencia) | R01, R03, R04, R05 | P04 un valor fuera de rango se rechaza, se conserva el ultimo valido y se registra ERROR (R01, R03, R04, R05). | `test_sistema.py::test_cp94_p04_fuera_de_rango_se_rechaza` | PASS |
| CP-95 | Sistema (archivos, bitacoras, concurrencia) | - | P05 texto donde se espera otro tipo: continua con el ultimo valor valido y registra ERROR. | `test_sistema.py::test_cp95_p05_formato_incorrecto_conserva_ultimo_valido` | PASS |
| CP-96 | Sistema (archivos, bitacoras, concurrencia) | R01 | P06 archivo vacio o clave faltante: se conserva el estado definido y se registra el error (R01). | `test_sistema.py::test_cp96_p06_dato_ausente_estado_definido` | PASS |
| CP-97 | Sistema (archivos, bitacoras, concurrencia) | - | P07 si el archivo se retira el sistema no termina; al volver se recupera y lo registra. | `test_sistema.py::test_cp97_p07_archivo_inexistente_no_termina` | PASS |
| CP-98 | Sistema (archivos, bitacoras, concurrencia) | - | P08 un escritor y el hilo lector trabajan a la vez: nunca se lee un valor parcial ni corrupto. | `test_sistema.py::test_cp98_p08_actualizacion_concurrente_sin_lecturas_parciales` | PASS |
| CP-99 | Sistema (archivos, bitacoras, concurrencia) | R02, R08 | P09 al superar un umbral critico se enciende el testigo y se registra un WARN prioritario (R02, R08). | `test_sistema.py::test_cp99_p09_advertencia_testigo_y_evento_prioritario` | PASS |
| CP-100 | Sistema (archivos, bitacoras, concurrencia) | - | P10 tras una entrada invalida, al corregirla se retoma la operacion sin reiniciar. | `test_sistema.py::test_cp100_p10_recuperacion_sin_reinicio` | PASS |
| CP-101 | Sistema (archivos, bitacoras, concurrencia) | - | P11 un archivo sin permiso de lectura se rechaza y se registra; al restaurar el permiso se recupera. | `test_sistema.py::test_cp101_p11_lectura_no_autorizada` | PASS |
| CP-102 | Sistema (archivos, bitacoras, concurrencia) | - | P11 un archivo de datos que cualquiera puede escribir no se usa y se registra el error. | `test_sistema.py::test_cp102_p11_archivo_escribible_por_cualquiera_se_rechaza` | PASS |
| CP-103 | Sistema (archivos, bitacoras, concurrencia) | - | P11 las bitacoras se crean solo para el dueno y su grupo (640) y la carpeta con 750. | `test_sistema.py::test_cp103_p11_bitacoras_con_minimo_privilegio` | PASS |
| CP-104 | Sistema (archivos, bitacoras, concurrencia) | - | P12 3000 ciclos con datos cambiantes: las bitacoras rotan y no crecen sin limite. | `test_sistema.py::test_cp104_p12_ejecucion_prolongada_acotada` | PASS |
| CP-105 | Sistema (archivos, bitacoras, concurrencia) | - | eventos.log lleva INFO y WARN, errores.log solo ERROR; cada linea tiene fecha, nivel, componente y evento. | `test_sistema.py::test_cp105_bitacoras_separadas_y_con_formato` | PASS |
| CP-106 | Sistema (archivos, bitacoras, concurrencia) | - | la configuracion se lee del archivo; si falta o es invalida se usan valores por defecto y se informa. | `test_sistema.py::test_cp106_configuracion_externa_y_valores_por_defecto` | PASS |
| CP-107 | Sistema (archivos, bitacoras, concurrencia) | - | lineas sin formato, claves desconocidas, duplicadas, valores enormes y archivos grandes se rechazan. | `test_sistema.py::test_cp107_entrada_maliciosa_no_se_usa` | PASS |
| CP-108 | Sistema (archivos, bitacoras, concurrencia) | - | el buzon productor-consumidor nunca acumula: guarda solo el snapshot mas reciente. | `test_sistema.py::test_cp108_buzon_conserva_solo_el_dato_mas_reciente` | PASS |
| CP-109 | Sistema (archivos, bitacoras, concurrencia) | - | cada tipo se codifica en el archivo y se decodifica sin perdida (booleano, entero, decimal, enumeracion). | `test_sistema.py::test_cp109_conversion_y_formato_son_inversos` | PASS |
| CP-110 | Sistema (archivos, bitacoras, concurrencia) | - | el mismo dato invalido o el mismo archivo ausente se registran una sola vez mientras duran. | `test_sistema.py::test_cp110_errores_repetidos_no_inundan_la_bitacora` | PASS |
| CP-111 | Sistema (archivos, bitacoras, concurrencia) | - | si la lectura falla de forma inesperada, el hilo lo registra y sigue funcionando. | `test_sistema.py::test_cp111_hilo_lector_registra_fallos_inesperados_y_sigue` | PASS |
| CP-112 | Sistema (archivos, bitacoras, concurrencia) | - | si el renombrado falla, el archivo original queda intacto y no quedan temporales. | `test_sistema.py::test_cp112_escritura_atomica_limpia_temporales_si_falla` | PASS |
| CP-113 | Sistema (archivos, bitacoras, concurrencia) | - | tools/escribir_dato.py valida y escribe de forma atomica; con --sin-validar permite provocar errores. | `test_sistema.py::test_cp113_herramienta_escribir_dato` | PASS |
| CP-114 | Sistema (archivos, bitacoras, concurrencia) | - | el proceso simulador escribe valores siempre validos para todo el recorrido. | `test_sistema.py::test_cp114_simulador_produce_datos_validos` | PASS |
| CP-115 | Sistema (archivos, bitacoras, concurrencia) | R01, R03, R08 | con la aplicacion abierta, cambiar el archivo de datos actualiza el tablero sin reiniciar (R01, R03, R08). | `test_sistema.py::test_cp115_aplicacion_lee_el_archivo_y_actualiza_sin_reiniciar` | PASS |
| CP-116 | Sistema (archivos, bitacoras, concurrencia) | - | sin archivo de configuracion se usan valores por defecto y se registra; un error de la interfaz se registra y no termina la aplicacion. | `test_sistema.py::test_cp116_modo_manual_y_errores_de_configuracion_e_interfaz` | PASS |
| CP-117 | Sistema (archivos, bitacoras, concurrencia) | R01, R02, R03, R04, R05, R07, R08 | el monitor registra encendido y apagado de cada advertencia una sola vez (R01, R02, R03, R04, R05, R07, R08). | `test_sistema.py::test_cp117_monitor_registra_cada_transicion_una_vez` | PASS |
| CP-118 | Sistema (archivos, bitacoras, concurrencia) | - | un archivo de datos con codificacion invalida y una configuracion sin secciones se rechazan sin detenerse. | `test_sistema.py::test_cp118_archivos_corruptos_no_detienen_el_sistema` | PASS |
| CP-119 | Sistema (archivos, bitacoras, concurrencia) | - | el proceso simulador termina limpio al recibir Ctrl+C. | `test_sistema.py::test_cp119_simulador_se_detiene_limpio_con_ctrl_c` | PASS |
| CP-120 | Odometro (elemento 11) | - | CP-ODO-01 a 120 km/h durante 45 s el odometro pasa de 000062 a 000063 (1.5 km). | `test_odometro.py::test_cp120_odo01_acumula_la_distancia_recorrida` | PASS |
| CP-121 | Odometro (elemento 11) | - | 300 ciclos de 100 ms a 120 km/h suman exactamente 1 km; el redondeo no deja 62.999. | `test_odometro.py::test_cp121_odo01_un_kilometro_exacto_sin_error_de_redondeo` | PASS |
| CP-122 | Odometro (elemento 11) | - | CP-ODO-02 desde 999999, a 360 km/h durante 15 s (1.5 km) el contador vuelve a 000000. | `test_odometro.py::test_cp122_odo02_vuelve_a_cero_al_pasar_del_maximo` | PASS |
| CP-123 | Odometro (elemento 11) | R01 | con velocidad 0 o con el motor apagado (R01) el odometro no avanza. | `test_odometro.py::test_cp123_no_avanza_detenido_ni_con_motor_apagado` | PASS |
| CP-124 | Odometro (elemento 11) | - | el valor inicial debe ser numerico y estar en 0-999999; velocidades o tiempos negativos no restan. | `test_odometro.py::test_cp124_odometro_valida_sus_entradas_y_nunca_retrocede` | PASS |
| CP-125 | Odometro (elemento 11) | - | CP-ODO-03 si datos/odometro.txt contiene abc, se inicia en 000000, se avisa y se registra ERROR. | `test_odometro.py::test_cp125_odo03_archivo_corrupto_inicia_en_cero_con_aviso` | PASS |
| CP-126 | Odometro (elemento 11) | - | si el archivo principal esta corrupto o falta, se recupera del respaldo .bak. | `test_odometro.py::test_cp126_respaldo_recupera_el_kilometraje` | PASS |
| CP-127 | Odometro (elemento 11) | - | guardar escribe el principal y el respaldo; al cargar se recupera el mismo kilometraje. | `test_odometro.py::test_cp127_persistencia_atomica_con_respaldo` | PASS |
| CP-128 | Odometro (elemento 11) | - | la primera vez, sin archivo ni respaldo, se inicia en 000000 sin error. | `test_odometro.py::test_cp128_primer_arranque_sin_archivos` | PASS |
| CP-129 | Odometro (elemento 11) | - | un valor fuera de rango, negativo o un archivo demasiado grande se rechazan. | `test_odometro.py::test_cp129_valores_invalidos_del_archivo` | PASS |
| CP-130 | Odometro (elemento 11) | - | un archivo con bytes que no son UTF-8 se rechaza sin detener el sistema. | `test_odometro.py::test_cp130_archivo_ilegible_o_con_codificacion_invalida` | PASS |
| CP-131 | Odometro (elemento 11) | - | un odometro.txt escribible por cualquiera se rechaza: nadie mas que el dueno puede alterar el kilometraje. | `test_odometro.py::test_cp131_kilometraje_manipulable_por_otros_se_rechaza` | PASS |
| CP-132 | Odometro (elemento 11) | - | un odometro.txt sin permiso de lectura se rechaza y se registra. | `test_odometro.py::test_cp132_kilometraje_sin_permiso_de_lectura` | PASS |
| CP-133 | Odometro (elemento 11) | - | odometro=999999 en datos/vehiculo.conf se rechaza (clave_no_permitida) y lo demas se aplica. | `test_odometro.py::test_cp133_el_odometro_no_se_escribe_desde_el_archivo_de_datos` | PASS |
| CP-134 | Odometro (elemento 11) | - | la ruta y la frecuencia de guardado del odometro se leen de la configuracion y se validan. | `test_odometro.py::test_cp134_configuracion_del_odometro` | PASS |
| CP-135 | Odometro (elemento 11) | - | la ventana dibuja el odometro de 6 digitos en el velocimetro y lo actualiza con la marcha. | `test_odometro.py::test_cp135_el_tablero_muestra_el_odometro` | PASS |
| CP-136 | Odometro (elemento 11) | - | la aplicacion recupera el kilometraje al iniciar, lo guarda al cerrar y avisa si el archivo es invalido. | `test_odometro.py::test_cp136_la_aplicacion_carga_y_guarda_el_kilometraje` | PASS |
| CP-137 | Odometro (elemento 11) | - | eventos.log registra INFO odometro_actualizado al cambiar el kilometro mostrado, incluida la vuelta a 000000. | `test_odometro.py::test_cp137_el_monitor_registra_cada_kilometro` | PASS |
| CP-138 | Robustez (auditoria y ataque QA) | R02, R04, R05 | 0.9999 bar, 110.01 C y 1.5001 bar del archivo encienden sus advertencias (R02, R04, R05; DEF-04). | `test_robustez.py::test_cp138_decimales_del_archivo_llegan_sin_redondear` | PASS |
| CP-139 | Robustez (auditoria y ataque QA) | - | un valor fuera de rango en el archivo muestra aviso en la ventana y se retira al corregirlo (P04; DEF-05). | `test_robustez.py::test_cp139_dato_rechazado_del_archivo_se_avisa_en_pantalla` | PASS |
| CP-140 | Robustez (auditoria y ataque QA) | - | si un ciclo de refresco lanza una excepcion, el siguiente ciclo queda programado (DEF-06). | `test_robustez.py::test_cp140_un_error_en_un_ciclo_no_congela_el_tablero` | PASS |
| CP-141 | Robustez (auditoria y ataque QA) | R06 | refresco_ms mayor a 100 se rechaza: con 1000 ms todas las muestras caen en la misma fase del parpadeo (R06; DEF-06). | `test_robustez.py::test_cp141_refresco_no_puede_ocultar_los_parpadeos` | PASS |
| CP-142 | Robustez (auditoria y ataque QA) | - | tras un retraso de 10 s, el cambio de velocidad no se aplica al tiempo anterior (DEF-07). | `test_robustez.py::test_cp142_odometro_integra_cada_tramo_con_su_velocidad` | PASS |
| CP-143 | Robustez (auditoria y ataque QA) | - | una segunda ventana con la misma carpeta no guarda el odometro y lo avisa; el kilometraje de la primera se conserva (DEF-08). | `test_robustez.py::test_cp143_dos_instancias_no_pierden_kilometraje` | PASS |
| CP-144 | Robustez (auditoria y ataque QA) | - | refresco_ms=50% y una ruta de bitacoras que es un archivo no detienen el arranque (DEF-09). | `test_robustez.py::test_cp144_configuracion_defectuosa_no_impide_arrancar` | PASS |
| CP-145 | Robustez (auditoria y ataque QA) | - | un archivo reemplazado con el mismo tamano y la misma fecha se vuelve a leer (DEF-10). | `test_robustez.py::test_cp145_reemplazo_con_igual_tamano_y_fecha_se_detecta` | PASS |
| CP-146 | Robustez (auditoria y ataque QA) | - | dos escritores simultaneos con escribir_dato.py no se pisan los cambios (DEF-10). | `test_robustez.py::test_cp146_escrituras_simultaneas_no_se_pierden` | PASS |
| CP-147 | Robustez (auditoria y ataque QA) | - | P12 no puede aprobar si el simulador termina con error o casi no escribe (DEF-11). | `test_robustez.py::test_cp147_p12_falla_si_el_productor_falla` | PASS |
| CP-148 | Robustez (auditoria y ataque QA) | - | el CSV de aceptacion rechaza 361 km/h (no lo recorta) y admite pasos del odometro (elemento 11) (DEF-12). | `test_robustez.py::test_cp148_aceptacion_rechaza_valores_fuera_de_rango_y_acepta_el_11` | PASS |
| CP-149 | Robustez (auditoria y ataque QA) | - | los digitos del odometro quedan por encima de la aguja del velocimetro (DEF-12). | `test_robustez.py::test_cp149_aguja_no_tapa_el_odometro` | PASS |
| CP-150 | Robustez (auditoria y ataque QA) | - | NaN e infinito se rechazan con ValueError; un NaN pasaba la validacion de rango (DEF-13). | `test_robustez.py::test_cp150_el_modelo_rechaza_nan_e_infinito` | PASS |
| CP-151 | Robustez (auditoria y ataque QA) | - | digitos no ASCII se rechazan en el archivo de datos y en el del odometro (DEF-14). | `test_robustez.py::test_cp151_solo_digitos_ascii` | PASS |
| CP-152 | Temas de la materia (senales, shell) | - | kill -TERM o Ctrl+C cierran el cluster en orden: guarda el kilometraje y registra el fin (DEF-15). | `test_materia.py::test_cp152_senal_produce_cierre_ordenado` | PASS |
| CP-153 | Temas de la materia (senales, shell) | - | el script de diagnostico valida argumentos y carpeta con codigos de salida distintos (tema 2.3). | `test_materia.py::test_cp153_diagnostico_valida_argumentos_y_rutas` | PASS |
| CP-154 | Temas de la materia (senales, shell) | - | el reporte cuenta eventos, clasifica el estado y admite rutas con espacios (tema 2.3). | `test_materia.py::test_cp154_diagnostico_clasifica_y_reporta` | PASS |
| CP-155 | Panel de control (mandos y atajos) | R01 | apagado todo queda en reposo; al dar contacto: ralenti 1000 rpm, aceite 1.5 bar y el agua se calienta (R01). | `test_panel.py::test_cp155_arranque_en_reposo_y_ralenti` | PASS |
| CP-156 | Panel de control (mandos y atajos) | - | en marcha las rpm siguen a la velocidad; el limitador nunca deja pasar de 8200; al subir de marcha bajan las rpm. | `test_panel.py::test_cp156_marchas_acoplan_rpm_y_limitador` | PASS |
| CP-157 | Panel de control (mandos y atajos) | - | el freno detiene el auto sin velocidades negativas; en neutral el acelerador solo sube las rpm. | `test_panel.py::test_cp157_freno_y_revoluciones_en_vacio` | PASS |
| CP-158 | Panel de control (mandos y atajos) | R02, R04, R05 | turbo con retraso (max 1.1 bar); las fallas llevan el turbo a > 1.5 (R05), el aceite < 1 (R02) y el agua > 110 (R04). | `test_panel.py::test_cp158_fallas_producen_cada_advertencia` | PASS |
| CP-159 | Panel de control (mandos y atajos) | - | 20 000 pasos con pedales, marchas, fallas y contacto al azar: cada lectura pasa la validacion del lector. | `test_panel.py::test_cp159_el_panel_nunca_produce_un_dato_invalido` | PASS |
| CP-160 | Panel de control (mandos y atajos) | - | contacto, marcha, acelerador y luces del panel quedan en datos/vehiculo.conf y el lector del tablero los acepta. | `test_panel.py::test_cp160_pedales_y_luces_llegan_al_archivo` | PASS |
| CP-161 | Panel de control (mandos y atajos) | - | el panel escribe la entrada invalida, deja de escribir 3 s y luego restaura datos validos. | `test_panel.py::test_cp161_entradas_invalidas_y_restauracion` | PASS |
| CP-162 | Panel de control (mandos y atajos) | - | un escenario de aceptacion se reproduce en el archivo paso a paso; los atajos existen y el ejecutor reporta su codigo. | `test_panel.py::test_cp162_escenarios_en_vivo_y_atajos` | PASS |
| CP-163 | Realismo y seguridad (elementos 12-15, ECU) | - | las claves opcionales se codifican y decodifican sin perdida (booleano, bits de estado, decimal y causa) y se rechazan fuera de tipo o de rango. | `test_realismo.py::test_cp163_claves_opcionales_tipos_y_rangos` | PASS |
| CP-164 | Realismo y seguridad (elementos 12-15, ECU) | - | un archivo de diez claves no genera errores ni claves opcionales; una opcional invalida conserva su ultimo valor (ERROR); la que deja de llegar vuelve a sin dato (INFO); motor=1 con contacto=0 es un dato_inconsistente. | `test_realismo.py::test_cp164_formato_de_diez_claves_compatible_y_consistencia` | PASS |
| CP-165 | Realismo y seguridad (elementos 12-15, ECU) | R01, R02 | con contacto y motor apagado, velocidad y temperatura se actualizan y el odometro avanza; RPM, aceite y turbo quedan en 0 y el testigo 9 apagado (D3, R01, R02); sin dato de contacto el cuadro sigue al motor como antes. | `test_realismo.py::test_cp165_contacto_separa_encendido_de_motor_activo` | PASS |
| CP-166 | Realismo y seguridad (elementos 12-15, ECU) | R08, R13 | al pasar la llave a contacto todos los testigos encienden 2 s y despues solo queda el de una falla real (R08); el monitor registra la prueba y ningun WARN por ella (R13-H 5.2.21.4). | `test_realismo.py::test_cp166_prueba_de_testigos_al_dar_contacto` | PASS |
| CP-167 | Realismo y seguridad (elementos 12-15, ECU) | R09 | puertas=1 enciende el testigo 12 ambar fijo con el auto detenido; en movimiento parpadea en rojo y se registra WARN prioritario puerta_abierta_en_movimiento (R09); los bits 1 y 2 nombran las puertas. | `test_realismo.py::test_cp167_puerta_abierta_fija_detenido_y_critica_en_movimiento` | PASS |
| CP-168 | Realismo y seguridad (elementos 12-15, ECU) | R10 | con contacto y cinturon sin abrochar el testigo 13 enciende fijo; sobre 10 km/h parpadea y se registra WARN cinturon_desabrochado_en_movimiento (R10); sin dato o abrochado queda apagado. | `test_realismo.py::test_cp168_cinturon_desabrochado` | PASS |
| CP-169 | Realismo y seguridad (elementos 12-15, ECU) | R11 | el combustible se muestra con el ciclo de 500 ms y en litros del tanque de 120 L; la reserva enciende con <= 12 % y se apaga con >= 15 % (histeresis) y se registra WARN combustible_reserva (R11). | `test_realismo.py::test_cp169_combustible_y_reserva_con_histeresis` | PASS |
| CP-170 | Realismo y seguridad (elementos 12-15, ECU) | R12 | falla_motor con una causa enciende el testigo 15 con su texto y registra WARN motor_detenido_por_proteccion; al volver a ninguna se registra INFO proteccion_motor_liberada (R12); el modelo rechaza tipos y rangos invalidos. | `test_realismo.py::test_cp170_proteccion_del_motor_y_validacion_del_modelo` | PASS |
| CP-171 | Realismo y seguridad (elementos 12-15, ECU) | - | la franja inferior del tablero dibuja la llave, el combustible con su reserva, la puerta, el cinturon y la proteccion; sin dato quedan apagados; aplicar_externo acepta claves sin control manual y None. | `test_realismo.py::test_cp171_tablero_dibuja_los_elementos_adicionales` | PASS |
| CP-172 | Realismo y seguridad (elementos 12-15, ECU) | R02, R12 | con fuga de aceite la ECU no deja arrancar y enclava la causa aceite (R02, R12); reparar no basta si el deposito quedo bajo 50 %; una fuga en marcha vacia el deposito y la ECU detiene el motor por falta de presion. | `test_realismo.py::test_cp172_fuga_de_aceite_no_deja_arrancar` | PASS |
| CP-173 | Realismo y seguridad (elementos 12-15, ECU) | R04, R12 | con el radiador danado el agua llega a 120 C, la ECU detiene el motor (R04, R12) y no deja arrancar hasta reparar y enfriar bajo 100 C; sin motor el auto no avanza aunque se acelere. | `test_realismo.py::test_cp173_sobrecalentamiento_detiene_el_motor_y_no_deja_moverse` | PASS |
| CP-174 | Realismo y seguridad (elementos 12-15, ECU) | R05, R12 | con la valvula de descarga fallando el turbo pasa de 1.5 bar; tras 1 s la ECU corta el motor y la proteccion queda enclavada hasta reparar (R05, R12). | `test_realismo.py::test_cp174_sobrepresion_del_turbo_corta_el_motor` | PASS |
| CP-175 | Realismo y seguridad (elementos 12-15, ECU) | R08 | con falla de frenos la eficiencia baja al 30 % y desde 100 km/h el auto tarda mas de 2.5 veces en detenerse (R08); cada frenada calienta los discos y en caliente la eficiencia baja hasta 60 % (fading). | `test_realismo.py::test_cp175_falla_de_frenos_frena_mal_y_los_frenos_calientes_pierden_eficiencia` | PASS |
| CP-176 | Realismo y seguridad (elementos 12-15, ECU) | R09 | con una puerta abierta la ECU bloquea la traccion: el auto no avanza aunque se acelere y se avisa una vez; al cerrar la puerta avanza (R09). | `test_realismo.py::test_cp176_puerta_abierta_impide_avanzar` | PASS |
| CP-177 | Realismo y seguridad (elementos 12-15, ECU) | R11, R12 | el consumo vacia el tanque (2 L/h en ralenti); sin combustible el motor se apaga, la ECU informa la causa combustible y no arranca hasta cargar (R11, R12). | `test_realismo.py::test_cp177_sin_combustible_el_motor_se_apaga_y_no_arranca` | PASS |
| CP-178 | Realismo y seguridad (elementos 12-15, ECU) | - | el panel separa llave y arranque, no arranca con fuga de aceite y lo avisa, escribe las claves opcionales que acepta el lector, la puerta abierta impide avanzar, el taller repara y el banco y el ciclo ECE-15 corren desde el panel. | `test_realismo.py::test_cp178_panel_llave_arranque_puertas_y_taller` | PASS |
| CP-179 | Banco de liberacion (normas de la epoca) | R13, R39 | las formulas de R13-H y R39 dan los valores del texto de la norma: tipo 0 a 100 km/h <= 70 m, dm de un caso calculado a mano, v1 = 120 y v2 = 60 km/h en el tipo I y los limites del velocimetro a 40, 80 y 120 km/h. | `test_liberacion.py::test_cp179_formulas_de_las_normas` | PASS |
| CP-180 | Banco de liberacion (normas de la epoca) | - | el perfil del ciclo urbano ECE-15 dura 195 s, llega a 50 km/h y su distancia integrada es 994.03 m. | `test_liberacion.py::test_cp180_perfil_del_ciclo_ece15` | PASS |
| CP-181 | Banco de liberacion (normas de la epoca) | - | la unidad sin fallas aprueba las 9 pruebas del banco y el odometro del cuadro mide el ciclo ECE-15 con menos de 1 % de error: APTO PARA PRODUCCION. | `test_liberacion.py::test_cp181_unidad_sana_apta_para_produccion` | PASS |
| CP-182 | Banco de liberacion (normas de la epoca) | R39 | cada falla del panel deja la unidad RECHAZADA y la detecta la prueba de su sistema: aceite en el arranque, radiador en el enfriamiento, turbo a plena carga, frenos en testigos, tipo 0 y tipo I, y velocimetro en R39 y el odometro. | `test_liberacion.py::test_cp182_cada_falla_la_rechaza_la_prueba_de_su_sistema` | PASS |
| CP-183 | Banco de liberacion (normas de la epoca) | - | tools/banco_liberacion.py --evidencia escribe el reporte con la matriz falla -> prueba y termina con 0 porque el banco distingue la unidad sana de cada falla; con una falla termina con 1. | `test_liberacion.py::test_cp183_herramienta_del_banco_deja_evidencia` | PASS |

## Resumen

- Casos de prueba: 193
- Pasaron: 193
- Fallo esperado por defecto abierto (XFAIL): 0
- Fallaron / otros: 0

## Casos por requisito

| Requisito | Casos |
|-----------|-------|
| R01 | CA-01, CA-02, CA-03, CA-07, CA-09, CA-10, CP-35, CP-36, CP-37, CP-51, CP-53, CP-54, CP-65, CP-66, CP-68, CP-73, CP-74, CP-91, CP-92, CP-93, CP-94, CP-96, CP-115, CP-117, CP-123, CP-155, CP-165 |
| R02 | CA-09, CP-03, CP-17, CP-18, CP-19, CP-20, CP-37, CP-43, CP-44, CP-70, CP-92, CP-93, CP-99, CP-117, CP-138, CP-158, CP-165, CP-172 |
| R03 | CA-03, CP-02, CP-13, CP-14, CP-15, CP-16, CP-27, CP-40, CP-41, CP-42, CP-69, CP-75, CP-92, CP-93, CP-94, CP-115, CP-117 |
| R04 | CA-04, CP-04, CP-21, CP-22, CP-23, CP-28, CP-45, CP-46, CP-69, CP-92, CP-93, CP-94, CP-117, CP-138, CP-158, CP-173 |
| R05 | CA-05, CP-05, CP-24, CP-25, CP-26, CP-29, CP-47, CP-48, CP-69, CP-92, CP-93, CP-94, CP-117, CP-138, CP-158, CP-174 |
| R06 | CA-06, CA-08, CP-06, CP-07, CP-08, CP-30, CP-49, CP-50, CP-57, CP-71, CP-141 |
| R07 | CA-07, CA-08, CP-09, CP-31, CP-33, CP-34, CP-58, CP-64, CP-65, CP-71, CP-72, CP-117 |
| R08 | CA-10, CP-09, CP-32, CP-59, CP-66, CP-72, CP-76, CP-99, CP-115, CP-117, CP-166, CP-175 |
| R09 | CP-167, CP-176 |
| R10 | CP-168 |
| R11 | CP-169, CP-177 |
| R12 | CP-170, CP-172, CP-173, CP-174, CP-177 |
| R13 | CP-166, CP-179 |
| R39 | CP-179, CP-182 |

Requisitos sin casos: ninguno
