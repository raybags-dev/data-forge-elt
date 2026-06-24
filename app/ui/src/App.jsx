import React, { useState } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import Crawlers from './pages/Crawlers.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Datasets from './pages/Datasets.jsx'
import Logs from './pages/Logs.jsx'
import Pipeline from './pages/Pipeline.jsx'
import ChatWidget from './components/ChatWidget.jsx'
import { TokenGateProvider } from './components/TokenGate.jsx'

export default function App() {
  const [chatOpen, setChatOpen] = useState(false)
  const [chatPreMessage, setChatPreMessage] = useState(null)

  function openChat(preMessage) {
    setChatPreMessage(preMessage || null)
    setChatOpen(true)
  }

  return (
    <TokenGateProvider onOpenChat={openChat}>
      <BrowserRouter basename="/dataforge">
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="pipeline" element={<Pipeline />} />
            <Route path="crawlers" element={<Crawlers />} />
            <Route path="datasets" element={<Datasets />} />
            <Route path="logs" element={<Logs />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <ChatWidget
        isOpen={chatOpen}
        onOpen={() => openChat()}
        onClose={() => { setChatOpen(false); setChatPreMessage(null) }}
        preMessage={chatPreMessage}
      />
    </TokenGateProvider>
  )
}
