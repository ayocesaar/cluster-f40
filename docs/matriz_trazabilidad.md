# Matriz de trazabilidad - Cluster F40

| CP | Tecnica | Requisito | Descripcion | Prueba | Resultado |
|----|---------|-----------|-------------|--------|-----------|
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

## Resumen

- Casos de prueba: 66
- Pasaron: 66
- Fallo esperado por defecto abierto (XFAIL): 0
- Fallaron / otros: 0

## Casos por requisito

| Requisito | Casos |
|-----------|-------|
| R01 | CP-35, CP-36, CP-37, CP-51, CP-53, CP-54, CP-65, CP-66 |
| R02 | CP-03, CP-17, CP-18, CP-19, CP-20, CP-37, CP-43, CP-44 |
| R03 | CP-02, CP-13, CP-14, CP-15, CP-16, CP-27, CP-40, CP-41, CP-42 |
| R04 | CP-04, CP-21, CP-22, CP-23, CP-28, CP-45, CP-46 |
| R05 | CP-05, CP-24, CP-25, CP-26, CP-29, CP-47, CP-48 |
| R06 | CP-06, CP-07, CP-08, CP-30, CP-49, CP-50, CP-57 |
| R07 | CP-09, CP-31, CP-33, CP-34, CP-58, CP-64, CP-65 |
| R08 | CP-09, CP-32, CP-59, CP-66 |

Requisitos sin casos: ninguno
