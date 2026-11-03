const BASE = import.meta.env.BASE_URL.replace(/\/$/, '');

/** Antepone la base del sitio a rutas internas ("/contacto/", "/uploads/foto.jpg"). */
export function url(path?: string | null): string {
  if (!path) return '';
  if (/^(https?:|mailto:|tel:|#|data:)/.test(path)) return path;
  if (path.startsWith('//')) return path;
  if (path.startsWith('/')) return BASE + path;
  return path;
}

/** Fecha en castellano: "21 de junio de 2026". */
export function fecha(d: Date): string {
  return new Intl.DateTimeFormat('es-AR', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' }).format(d);
}

/** Separa un texto en párrafos (doble salto de línea). */
export function parrafos(texto?: string | null): string[] {
  return (texto || '').split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean);
}
