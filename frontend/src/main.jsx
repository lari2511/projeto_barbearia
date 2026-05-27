import React from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import MobileShell from './components/MobileShell'
import AuthProvider from './context/AuthProvider'
import './index.css'

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <MobileShell>
          <App />
        </MobileShell>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
)
