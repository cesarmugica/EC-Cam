# Reporte para el autor de Topo

EC-Cam se construyó sobre [Topo](https://github.com/filirnd/topo) (licencia MIT). En el camino encontramos fallas y comportamientos de la nube de Tapo que también afectan a quien usa Topo. Este reporte se los comparte de vuelta al autor.

- **[ISSUE.md](ISSUE.md):** el texto en inglés, listo para pegar como *issue*.

## Qué incluye (resumen en español)

1. **Firmwares nuevos (C200 1.3.17 build 58281) no mandan video** hasta que se les pide con la petición de vista previa, más confirmaciones cada 25 partes y un latido cada 20 s.
2. Topo **mezcla las respuestas JSON de la cámara con el video**.
3. **Un visor nuevo reinicia la cámara para todos**, y quien entra a media transmisión recibe un MP4 cortado, lo que provoca reconexiones en bucle.
4. Detalles menores:
   - las cámaras siguen transmitiendo aunque nadie las vea;
   - las colas de los visores lentos crecen sin límite;
   - el navegador solo abre 6 conexiones a la vez con el mismo servidor.
5. Grabaciones de la SD:
   - la búsqueda de un día completo regresa vacía si hay muchos clips (hay que paginar);
   - no se puede reproducir con el en vivo abierto (`-52207`);
   - la reproducción también necesita confirmaciones;
   - pregunta abierta: el error `-52402` en el firmware 58281.

## Cómo enviarlo

1. Entra a <https://github.com/filirnd/topo/issues> con tu cuenta de GitHub y dale **New issue**.
2. Título sugerido: *Findings from a fork: newer C200 firmware needs the preview request, plus a few streaming/playback fixes*
3. Copia el contenido de [ISSUE.md](ISSUE.md) **sin el comentario de arriba** (lo que está entre `<!--` y `-->`) y pégalo como descripción.
4. **Create**.

El reporte no menciona tu nombre, tus cámaras ni enlaza a este repositorio (es privado). Si el autor pide el código, se le puede compartir aparte.
