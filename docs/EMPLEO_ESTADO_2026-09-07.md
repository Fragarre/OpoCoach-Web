# Empleo — estado consolidado

**Fecha:** 7 de septiembre de 2026

## Arquitectura

El módulo Empleo utiliza el backend independiente `Fragarre/NetReto-Web-Empleo` y su base de datos Supabase independiente. Este repositorio contiene la integración frontend dentro de NetExamenes.

## Estado funcional

La primera fase está limitada a:

- Generalitat Valenciana (GVA).
- Diputación Provincial de Valencia (BOP Valencia).

El catálogo visible contiene actualmente **10 oportunidades: 7 GVA + 3 Diputación de Valencia**.

El catálogo excluye procedimientos que no representan una oportunidad de acceso para el opositor, incluidos promoción interna, libre designación, concurso general de méritos, concurso de traslados, comisiones de servicio, difícil cobertura y acto único telemático.

Las convocatorias no desaparecen por haber terminado el plazo de inscripción: permanecen mientras el proceso selectivo siga activo.

## Navegación

- `/empleo`: catálogo de oportunidades.
- `/empleo/proceso/[id]`: ficha individual de una convocatoria.
- `/empleo/seguimiento`: convocatorias seguidas y sus novedades.

Durante las cargas del catálogo se bloquean cambios consecutivos de organismo y se muestra un indicador de carga.

## Seguimiento y novedades

`Mi seguimiento` muestra las convocatorias seguidas y un único bloque denominado **«Novedades de mis convocatorias»**.

Las novedades pueden ser publicaciones oficiales o cambios relevantes. Las designaciones del órgano técnico de selección se clasifican como `TRIBUNAL`. Las publicaciones técnicas irrelevantes, como `Navegación`, se excluyen.

En `/empleo` se muestra un aviso cuando existen novedades pendientes y permite acceder directamente a `Mi seguimiento`.

No existe envío de correo ni vigilancia automática mediante cron.

## Criterio de continuidad

No introducir nuevos organismos en esta fase hasta completar y validar el funcionamiento de GVA y Diputación de Valencia. Las mejoras posteriores deben conservar la separación entre proceso selectivo, publicaciones, cambios y seguimiento del usuario.