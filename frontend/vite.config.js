import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Em desenvolvimento, as chamadas para /api vão para o FastAPI na porta 8000.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // permite abrir pelo celular na mesma rede Wi-Fi (útil no Workshop)
    proxy: { '/api': 'http://localhost:8000' },
  },
})
