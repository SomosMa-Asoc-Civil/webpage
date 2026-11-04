# Sitio web de SomosMa – Monomarentales Argentina

Sitio estático hecho con [Astro](https://astro.build), publicado gratis en **GitHub Pages** y editable desde **[Pages CMS](https://pagescms.org)** sin tocar código.

Reemplaza al WordPress anterior (hosting en DonWeb) manteniendo las mismas direcciones de las páginas y noticias.

## Cómo funciona

```
Pages CMS (editoras) ──commit──▶ este repo ──GitHub Actions──▶ GitHub Pages
```

- **No hay base de datos.** El contenido vive en el repo:
  - `src/content/noticias/*.md` → una noticia por archivo. El nombre del archivo es la dirección: `deudores-afuera.md` → `/deudores-afuera/`.
  - `src/data/*.json` → textos de las páginas (Inicio, Nosotras, Qué hacemos, Sumate, Contacto) y la configuración general (menú, redes, mail, clave del formulario).
  - `public/uploads/` → imágenes y archivos (misma estructura que `wp-content/uploads`).
- **Formularios** (Contacto y Sumate): [Web3Forms](https://web3forms.com), envía los mensajes por mail. La clave va en `src/data/sitio.json → formularios.web3forms_key` (también editable desde el CMS en *Configuración del sitio*). Mientras esté vacía, el formulario avisa que no está configurado y muestra el mail.
- **Publicación automática:** cada cambio en `main` dispara `.github/workflows/deploy.yml`, que construye y publica en 1–2 minutos.

## Puesta en marcha (una sola vez)

1. **Imágenes.** En Windows, desde la raíz del repo:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/migracion/descargar-imagenes.ps1
   ```
   Baja las ~130 imágenes del WordPress a `public/uploads/`. Se puede repetir: saltea las que ya están. Hay que hacerlo **antes de que venza el hosting**.
2. **Dependencias y prueba local:**
   ```bash
   npm install
   npm run dev      # http://localhost:4321
   npm run build    # verifica que todo compile
   ```
   Subí también el `package-lock.json` que genera `npm install`.
3. **GitHub Pages:** en el repo, *Settings → Pages → Build and deployment → Source: **GitHub Actions***.
4. **Pages CMS:** entrar a [app.pagescms.org](https://app.pagescms.org) con la cuenta de GitHub, elegir el repo `SomosMa-Asoc-Civil/webpage`. La configuración ya está en `.pages.yml`.
   - Para sumar editoras sin cuenta de GitHub: en Pages CMS, sección *Collaborators*, invitarlas por mail.
5. **Formularios:** generar la clave en web3forms.com **con el mail de la asociación** y pegarla en *Configuración del sitio → Formularios*.

## Instagram (publicaciones en la portada)

Igual que el plugin Spotlight del WordPress viejo: el sitio **muestra** las últimas publicaciones de
@monomarentalesargentina (no publica nada en Instagram).

- `.github/workflows/instagram.yml` corre todos los días a las 7:37 (hora de Argentina).
- `scripts/instagram/actualizar.mjs` trae las últimas publicaciones (por defecto 3; se cambia con `cantidad` en `src/data/instagram.json`), guarda las imágenes en `public/uploads/instagram/` y, si hay novedades, hace commit y vuelve a publicar el sitio.
- Los lunes, `scripts/instagram/renovar-token.mjs` renueva el token (dura 60 días) y lo guarda solo.
- Si no hay token o Instagram falla, el sitio sigue funcionando con lo último que tenía (o con las publicaciones cargadas a mano en el CMS).

### Configuración (una sola vez)

1. **Cuenta profesional.** En la app de Instagram: *Configuración → Tipo de cuenta y herramientas → Cambiar a cuenta profesional* (Creador o Empresa, gratis). La API no funciona con cuentas personales.
2. **App de Meta.** En [developers.facebook.com](https://developers.facebook.com/apps) crear una app → caso de uso de **Instagram** (API con inicio de sesión de Instagram) → *Configuración de la API con inicio de sesión de Instagram* → *Generar tokens de acceso* → agregar la cuenta @monomarentalesargentina e iniciar sesión → copiar el token. Si la app está en modo desarrollo y lo pide, sumar la cuenta como *Tester de Instagram* (Roles de la app) y aceptar la invitación desde Instagram (*Configuración → Apps y sitios web*).
3. **Secretos del repo** (*Settings → Secrets and variables → Actions → New repository secret*):
   - `IG_TOKEN`: el token del paso 2.
   - `IG_GH_PAT`: un token de GitHub *fine-grained* ([crear acá](https://github.com/settings/personal-access-tokens/new)) con acceso solo a este repo y permiso **Secrets: Read and write**. Sirve para guardar el token de Instagram renovado. Anotar cuándo vence para generarlo de nuevo.
4. **Primera corrida.** *Actions → Actualizar Instagram → Run workflow*. En un par de minutos aparecen las publicaciones en la portada.

> Al dar de baja el WordPress, quitar el acceso de Spotlight en Instagram (*Configuración → Apps y sitios web*): su token quedó dentro del export XML.

## Dominio somosma.com.ar (cuando se recupere el acceso)

1. Delegar el dominio a Cloudflare (gratis) desde la cuenta de DonWeb, o pedir la transferencia a nombre de la asociación en NIC Argentina.
2. En Cloudflare: `CNAME www → somosma-asoc-civil.github.io` y los registros `A` del dominio raíz a las IPs de GitHub Pages (185.199.108.153, .109.153, .110.153, .111.153).
3. En el repo: *Settings → Pages → Custom domain* → `somosma.com.ar` y activar *Enforce HTTPS*.
4. No hace falta tocar código: la base de las rutas se ajusta sola en el build.

## Estructura

```
.pages.yml                    configuración del CMS
astro.config.mjs              base de rutas (BASE_PATH) para github.io / dominio propio
src/
  content/noticias/           noticias en Markdown
  data/                       textos de páginas en JSON
  layouts/Base.astro          cabecera, menú, pie y metadatos para compartir
  components/                 formulario, tarjeta de noticia, íconos
  pages/                      una ruta por página; [slug].astro = noticias
  styles/global.css           paleta y tipografías del sitio original (Poppins + Roboto)
public/uploads/               imágenes
scripts/migracion/            script de migración desde WordPress y descarga de imágenes
```

## Notas de la migración

- Se migraron 8 noticias, 5 páginas y el equipo de Nosotras (10 integrantes) desde el export de WordPress del 03/11/2026.
- Las noticias respetan el formato que les dio cada autora en WordPress: citas destacadas, versos y textos preformateados (usados como epígrafes), texto centrado, citas en violeta, espaciadores y fotos achicadas. Esos bloques quedaron en HTML dentro del `.md`, con las clases de WordPress, y sus estilos están en `src/styles/global.css` (sección `.prosa`), medidos sobre las notas publicadas.
- `/noticias-2/` (dirección vieja) redirige a `/noticias/`.
- El feed de Instagram (plugin Spotlight) se reemplazó por una sincronización diaria con GitHub Actions (ver sección Instagram).
- En Nosotras hay dos nombres que parecen tener errores de tipeo en el original ("Paola Uquizo" / "Urquizo", "Piertropaolo" / "Pietropaolo"); se dejaron como estaban para que lo confirmen.
