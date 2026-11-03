import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

// Cada noticia es un archivo .md en src/content/noticias (se editan desde Pages CMS).
// El nombre del archivo es la dirección de la nota: deudores-afuera.md -> /deudores-afuera/
const noticias = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/noticias' }),
  schema: z.object({
    title: z.string(),
    date: z.coerce.date(),
    author: z.string().default('SomosMa'),
    image: z.string().optional().default(''),
    excerpt: z.string().optional().default(''),
    categories: z.array(z.string()).optional().default([]),
    tags: z.array(z.string()).optional().default([]),
    draft: z.boolean().optional().default(false),
  }),
});

export const collections = { noticias };
