// @ts-check
import { defineConfig } from 'astro/config';

/**
 * BASE_PATH y SITE_URL los completa GitHub Actions (actions/configure-pages):
 * - Mientras el sitio vive en https://<org>.github.io/webpage -> BASE_PATH=/webpage
 * - Cuando se conecte somosma.com.ar (dominio propio)        -> BASE_PATH vacío
 * En local (npm run dev) no hace falta definir nada.
 */
const BASE = (process.env.BASE_PATH || '').replace(/\/$/, '');
const SITE = process.env.SITE_URL || 'https://somosma.com.ar';

/**
 * Las noticias se escriben con rutas absolutas (/uploads/..., /contacto/).
 * Este plugin les antepone BASE_PATH para que funcionen también en <org>.github.io/webpage.
 */
function rehypeBasePath() {
  return (tree) => {
    if (!BASE) return;
    const walk = (node) => {
      if (node.type === 'element' && node.properties) {
        for (const attr of ['src', 'href']) {
          const v = node.properties[attr];
          if (typeof v === 'string' && v.startsWith('/') && !v.startsWith('//') && !v.startsWith(BASE + '/')) {
            node.properties[attr] = BASE + v;
          }
        }
      }
      if (node.children) node.children.forEach(walk);
    };
    walk(tree);
  };
}

export default defineConfig({
  site: SITE,
  base: BASE || '/',
  trailingSlash: 'ignore',
  build: { format: 'directory' },
  markdown: {
    rehypePlugins: [rehypeBasePath],
  },
});
