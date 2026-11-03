#!/usr/bin/env node
/**
 * Renueva el token de Instagram (dura 60 días; se puede renovar si tiene más de 24 horas)
 * y lo guarda de nuevo como secreto del repo.
 *
 * Variables de entorno:
 *   IG_TOKEN    token actual
 *   GH_TOKEN    token de GitHub con permiso de escritura sobre "Secrets" del repo
 *   GITHUB_REPOSITORY  owner/repo (lo define GitHub Actions)
 *
 * Usa la CLI `gh` (viene instalada en los runners de GitHub).
 */
import { execFileSync } from 'node:child_process';

const token = process.env.IG_TOKEN?.trim();
if (!token) {
  console.log('IG_TOKEN no está configurado: nada para renovar.');
  process.exit(0);
}
if (!process.env.GH_TOKEN) {
  console.log('Falta el secreto IG_GH_PAT: no se puede guardar el token renovado. Ver README > Instagram.');
  process.exit(0);
}

const r = await fetch(
  `https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token=${encodeURIComponent(token)}`,
);
const cuerpo = await r.json().catch(() => ({}));
if (!r.ok || !cuerpo.access_token) {
  console.error(`No se pudo renovar el token: ${cuerpo.error?.message || `HTTP ${r.status}`}`);
  process.exit(1);
}

execFileSync('gh', ['secret', 'set', 'IG_TOKEN', '--repo', process.env.GITHUB_REPOSITORY, '--body', cuerpo.access_token], {
  stdio: ['ignore', 'inherit', 'inherit'],
});
const dias = Math.round((cuerpo.expires_in || 0) / 86400);
console.log(`Token renovado. Vence en ${dias} días.`);
