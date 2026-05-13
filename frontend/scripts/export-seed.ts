// Gera backend/seed.json a partir dos dados do TypeScript
// Uso: bun run scripts/export-seed.ts
import { INGREDIENTS } from '../src/data/ingredients'
import { writeFileSync } from 'fs'
import { resolve } from 'path'

const out = resolve(import.meta.dir, '../../backend/seed.json')
writeFileSync(out, JSON.stringify(INGREDIENTS, null, 2))
console.log(`✓ ${INGREDIENTS.length} ingredientes exportados → ${out}`)
