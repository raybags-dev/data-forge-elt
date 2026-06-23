import React from 'react'
import ReactDOM from 'react-dom/client'
import { Toaster } from 'react-hot-toast'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
    <Toaster
      position="top-right"
      toastOptions={{
        style: {
          background: '#1e293b',
          color: '#f1f5f9',
          border: '1px solid #334155',
        },
      }}
    />
  </React.StrictMode>,
)

// Remove the HTML loader overlay once React has painted its first frame
requestAnimationFrame(() => {
  requestAnimationFrame(() => {
    const loader = document.getElementById('app-loader')
    if (loader) {
      loader.classList.add('fade-out')
      setTimeout(() => loader.remove(), 380)
    }
  })
})
