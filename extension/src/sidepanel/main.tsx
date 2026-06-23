import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { SidepanelLayout } from './components/SidepanelLayout'
import '@/styles/globals.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <SidepanelLayout />
  </StrictMode>,
)
