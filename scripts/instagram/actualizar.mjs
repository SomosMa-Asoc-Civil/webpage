#!/usr/bin/env node
/**
 * Trae las últimas publicaciones de Instagram y las deja listas para el sitio:
 *   - imágenes en public/uploads/instagram/<id>.jpg
 *   - datos en src/data/instagram.json
 *
 * Lo corre GitHub Actions todos los días (.github/workflows/instagram.yml).
 * Usa la "Instagram API with Instagram Login" de Meta (requiere cuenta profesional).
 *
 * Variables de entorno:
 *   IG_TOKEN     token de acceso de larga duración (secreto del repo)
 *   IG_CANTIDAD  cuántas publicaciones guardar (por defecto, la que diga instagram.json o 3)
 *
 * Uso local:  IG_TOKEN=xxxx node scripts/instagram/actualizar.mjs
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const DATOS = path.join(RAIZ, 'src/data/instagram.json');
const CARPETA = path.join(RAIZ, 'public/uploads/instagram');
const API = 'https://graph.instagram.com';

const token = process.env.IG_TOKEN?.trim();
if (!token) {
  console.log('IG_TOKEN no está configurado: no se actualiza Instagram (el sitio sigue funcionando).');
  process.exit(0);
}

const leerJSON = async (archivo, porDefecto) => {
  try {
    return JSON.parse(await fs.readFile(archivo, 'utf8'));
  } catch {
    return porDefecto;
  }
};

const anterior = await leerJSON(DATOS, { usuario: 'monomarentalesargentina', cantidad: 3, publicaciones: [] });
const cantidad = Number(process.env.IG_CANTIDAD) || Number(anterior.cantidad) || 3;

async function pedir(url) {
  const r = await fetch(url);
  const cuerpo = await r.json().catch(() => ({}));
  if (!r.ok || cuerpo.error) {
    const msg = cuerpo.error?.message || `HTTP ${r.status}`;
    throw new Error(`Instagram respondió con un error: ${msg}`);
  }
  return cuerpo;
}

const campos = 'id,caption,media_type,media_url,thumbnail_url,permalink,timestamp';
const perfil = await pedir(`${API}/me?fields=username&access_token=${encodeURIComponent(token)}`);
// Se piden de más porque se descartan las que no tienen imagen
const lista = await pedir(`${API}/me/media?fields=${campos}&limit=${cantidad + 6}&access_token=${encodeURIComponent(token)}`);

await fs.mkdir(CARPETA, { recursive: true });
const publicaciones = [];
for (const m of lista.data ?? []) {
  if (publicaciones.length >= cantidad) break;
  // En los videos se usa la miniatura; en los carruseles, la primera imagen
  const origen = m.media_type === 'VIDEO' ? m.thumbnail_url : m.media_url;
  if (!origen) continue;
  const archivo = `${m.id}.jpg`;
  const destino = path.join(CARPETA, archivo);
  try {
    await fs.access(destino);
  } catch {
    const r = await fetch(origen);
    if (!r.ok) {
      console.warn(`No se pudo bajar la imagen de ${m.permalink} (HTTP ${r.status}), se saltea.`);
      continue;
    }
    await fs.writeFile(destino, Buffer.from(await r.arrayBuffer()));
    console.log(`Nueva: ${m.permalink}`);
  }
  publicaciones.push({
    id: m.id,
    imagen: `/uploads/instagram/${archivo}`,
    url: m.permalink,
    texto: (m.caption || '').split('\n')[0].slice(0, 140),
    fecha: m.timestamp,
    tipo: m.media_type,
  });
}

if (publicaciones.length === 0) {
  console.log('Instagram no devolvió publicaciones con imagen; se mantiene lo anterior.');
  process.exit(0);
}

// Borra las imágenes de publicaciones que ya no se muestran
const enUso = new Set(publicaciones.map((p) => path.basename(p.imagen)));
for (const f of await fs.readdir(CARPETA)) {
  if (f.endsWith('.jpg') && !enUso.has(f)) await fs.rm(path.join(CARPETA, f));
}

const nuevo = {
  usuario: perfil.username || anterior.usuario,
  cantidad,
  actualizado: new Date().toISOString(),
  publicaciones,
};
// Solo se escribe si cambió algo además de la fecha, para no generar commits vacíos
const sinFecha = (o) => JSON.stringify({ ...o, actualizado: undefined });
if (sinFecha(nuevo) === sinFecha(anterior)) {
  console.log('Sin publicaciones nuevas.');
} else {
  await fs.writeFile(DATOS, JSON.stringify(nuevo, null, 2) + '\n');
  console.log(`Actualizado: ${publicaciones.length} publicaciones de @${nuevo.usuario}.`);
}
