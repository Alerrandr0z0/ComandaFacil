import { Routes, Route, Navigate } from 'react-router-dom'

// Pages will be imported here as they are implemented
const PlaceholderPage = ({ name }: { name: string }) => (
  <div className="flex min-h-screen items-center justify-center">
    <div className="text-center">
      <h1 className="text-3xl font-bold text-brand-400">ComandaFácil</h1>
      <p className="mt-2 text-gray-400">{name} — em construção</p>
    </div>
  </div>
)

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<PlaceholderPage name="Dashboard" />} />
      <Route path="/login" element={<PlaceholderPage name="Login" />} />
      <Route path="/menu" element={<PlaceholderPage name="Cardápio" />} />
      <Route path="/orders" element={<PlaceholderPage name="Pedidos" />} />
      <Route path="/kitchen" element={<PlaceholderPage name="Cozinha" />} />
      <Route path="/stock" element={<PlaceholderPage name="Estoque" />} />
      <Route path="/analytics" element={<PlaceholderPage name="Analytics" />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
