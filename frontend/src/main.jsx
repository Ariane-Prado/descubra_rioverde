import React from 'react'
import ReactDOM from 'react-dom/client'
import '@fontsource-variable/inter' // fonte embutida: funciona sem internet
import App from './App.jsx'
import './App.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
