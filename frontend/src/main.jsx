import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 3500,
          style: {
            background: 'rgba(10,10,37,0.95)',
            border: '1px solid rgba(0,212,255,0.2)',
            color: '#E2E8F0',
            backdropFilter: 'blur(16px)',
            fontSize: '13px',
          },
          success: { iconTheme: { primary: '#06FFA5', secondary: '#050515' } },
          error:   { iconTheme: { primary: '#FF4D6D', secondary: '#050515' } },
        }}
      />
    </BrowserRouter>
  </React.StrictMode>
)
