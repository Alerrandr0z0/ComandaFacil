import axios from 'axios'
import { type FormEvent, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/features/auth/auth_context'

export default function LoginPage() {
  const { login, employee } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [tenantId, setTenantId] = useState('1')
  const [errors, setErrors] = useState<{ [key: string]: string }>({})
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const validate = () => {
    // ... (rest of validate function remains the same, need to be careful with edit tool)
    const newErrors: { [key: string]: string } = {}
    if (!email) {
      newErrors.email = 'E-mail é obrigatório'
    } else if (!/\S+@\S+\.\S+/.test(email)) {
      newErrors.email = 'E-mail corporativo inválido'
    }

    if (!password) {
      newErrors.password = 'Senha é obrigatória'
    } else if (password.length < 6) {
      newErrors.password = 'A senha deve conter no mínimo 6 caracteres'
    }

    const tId = Number(tenantId)
    if (!tenantId) {
      newErrors.tenantId = 'ID da franquia é obrigatório'
    } else if (Number.isNaN(tId) || !Number.isInteger(tId)) {
      newErrors.tenantId = 'ID da franquia deve ser um número inteiro'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!validate()) return

    setIsSubmitting(true)
    setErrorMsg(null)
    try {
      await login(email, password, Number(tenantId))
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.data?.detail) {
        setErrorMsg(err.response.data.detail as string)
      } else {
        setErrorMsg('Erro de conexão ou credenciais inválidas.')
      }
      setIsSubmitting(false)
      return
    }
  }

  useEffect(() => {
    if (employee) {
      if (employee.role === 'SUPER_ADMIN') {
        navigate('/admin')
      } else {
        navigate('/orders')
      }
    }
  }, [employee, navigate])

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-gray-950 px-4">
      {/* Dynamic Aurora Gradient Background */}
      <div className="absolute top-[-20%] left-[-10%] h-[600px] w-[600px] rounded-full bg-brand-500/10 blur-[150px]" />
      <div className="absolute bottom-[-10%] right-[-10%] h-[500px] w-[500px] rounded-full bg-purple-500/10 blur-[130px]" />

      {/* Glassmorphic Form Card */}
      <div className="z-10 w-full max-w-md rounded-2xl border border-gray-800/50 bg-gray-900/60 p-8 shadow-2xl backdrop-blur-xl">
        <div className="text-center">
          <h1 className="bg-gradient-to-r from-brand-400 to-amber-500 bg-clip-text text-4xl font-extrabold text-transparent tracking-tight">
            ComandaFácil
          </h1>
          <p className="mt-2 text-sm text-gray-400">Sistema de Gestão de Franquias</p>
        </div>

        <form onSubmit={onSubmit} className="mt-8 space-y-6">
          {errorMsg && (
            <div className="rounded-lg border border-red-900/50 bg-red-950/40 p-3 text-center text-sm font-medium text-red-400 backdrop-blur-sm">
              {errorMsg}
            </div>
          )}

          <div>
            <label htmlFor="tenantId" className="block text-sm font-semibold text-gray-300">
              ID da Franquia
            </label>
            <input
              id="tenantId"
              type="number"
              value={tenantId}
              onChange={(e) => setTenantId(e.target.value)}
              className="mt-2 w-full rounded-xl border border-gray-800 bg-gray-950/50 px-4 py-3 text-sm text-white placeholder-gray-600 shadow-inner focus:border-brand-500 focus:ring-1 focus:ring-brand-500 focus:outline-none transition-all"
              placeholder="Ex: 1"
            />
            {errors.tenantId && (
              <p className="mt-1 text-xs font-medium text-red-400">{errors.tenantId}</p>
            )}
          </div>

          <div>
            <label htmlFor="email" className="block text-sm font-semibold text-gray-300">
              E-mail Corporativo
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-2 w-full rounded-xl border border-gray-800 bg-gray-950/50 px-4 py-3 text-sm text-white placeholder-gray-600 shadow-inner focus:border-brand-500 focus:ring-1 focus:ring-brand-500 focus:outline-none transition-all"
              placeholder="seuemail@empresa.com"
            />
            {errors.email && (
              <p className="mt-1 text-xs font-medium text-red-400">{errors.email}</p>
            )}
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-semibold text-gray-300">
              Senha
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-2 w-full rounded-xl border border-gray-800 bg-gray-950/50 px-4 py-3 text-sm text-white placeholder-gray-600 shadow-inner focus:border-brand-500 focus:ring-1 focus:ring-brand-500 focus:outline-none transition-all"
              placeholder="Sua senha secreta"
            />
            {errors.password && (
              <p className="mt-1 text-xs font-medium text-red-400">{errors.password}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="flex w-full items-center justify-center rounded-xl bg-gradient-to-r from-brand-500 to-amber-600 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-brand-500/10 hover:brightness-110 active:brightness-95 disabled:pointer-events-none disabled:opacity-50 transition-all duration-300"
          >
            {isSubmitting ? (
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
            ) : (
              'Entrar no Painel'
            )}
          </button>
        </form>
      </div>
    </div>
  )
}
