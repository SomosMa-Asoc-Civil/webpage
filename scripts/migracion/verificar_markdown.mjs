// Recibe un JSON con bloques Markdown y devuelve los índices que no se renderizan bien
// (quedan asteriscos o guiones bajos sueltos). Lo usa migrar_wordpress.py.
import fs from 'fs';
// Usa `marked` del proyecto (npm install) o, si no está, la ruta indicada en MARKED_PATH
let marked;
try {
  ({ marked } = await import('marked'));
} catch {
  ({ marked } = await import(process.env.MARKED_PATH || 'marked'));
}
const bloques = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const malos = [];
bloques.forEach((b, i) => {
  const texto = marked.parse(b.replace(/\\\*/g, '')).replace(/<[^>]+>/g, '');
  if (/\*|(^|\s)_\S|\S_(\s|$)/.test(texto)) malos.push(i);
});
process.stdout.write(JSON.stringify(malos));
