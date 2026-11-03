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

/**
 * Texto simple -> HTML seguro, por párrafos.
 * - Línea en blanco: párrafo nuevo
 * - Salto de línea: <br>
 * - **texto**: negrita
 * - _texto_: cursiva
 */
export function formato(texto?: string | null): string[] {
  const escapar = (s: string) =>
    s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  return parrafos(texto).map((p) =>
    escapar(p)
      .replace(/\*\*([\s\S]+?)\*\*/g, '<strong>$1</strong>')
      .replace(/(^|[\s(“"])_(\S[\s\S]*?\S|\S)_(?=$|[\s.,;:!?)”"])/g, '$1<em>$2</em>')
      .replace(/\n/g, '<br />'),
  );
}

/** Igual que formato() pero todo en un solo bloque (para títulos o datos cortos). */
export function formatoLinea(texto?: string | null): string {
  return formato(texto).join('<br />');
}

/** Separa un texto en párrafos (doble salto de línea). */
export function parrafos(texto?: string | null): string[] {
  return (texto || '').split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean);
}
