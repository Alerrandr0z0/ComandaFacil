import { ExternalLink, Mail, Phone, Plus, Search, ShieldCheck } from 'lucide-react'
import type React from 'react'
import { useState } from 'react'

interface Supplier {
  id: number
  name: string
  category: string
  status: 'HOMOLOGADO' | 'EM_ANALISE' | 'SUSPENSO'
  contactName: string
  email: string
  phone: string
}

const INITIAL_SUPPLIERS: Supplier[] = [
  {
    id: 1,
    name: 'Distribuidora Ambev Central',
    category: 'Bebidas e Cervejas',
    status: 'HOMOLOGADO',
    contactName: 'Carlos Eduardo',
    email: 'carlos.eduardo@ambev.com.br',
    phone: '(11) 98765-4321',
  },
  {
    id: 2,
    name: 'Coca-Cola FEMSA Brasil',
    category: 'Refrigerantes e Águas',
    status: 'HOMOLOGADO',
    contactName: 'Luciana Mota',
    email: 'luciana.mota@femsa.com.br',
    phone: '(11) 97654-3210',
  },
  {
    id: 3,
    name: 'Hortifruti Orgânicos Vale Verde',
    category: 'Hortifruti e Insumos Secos',
    status: 'HOMOLOGADO',
    contactName: 'Marcos Silva',
    email: 'marcos@valeverdeorganicos.com',
    phone: '(21) 96543-2109',
  },
  {
    id: 4,
    name: 'Carnes Nobres Distribuição',
    category: 'Proteínas e Congelados',
    status: 'EM_ANALISE',
    contactName: 'Ricardo Santos',
    email: 'contato@carnesnobresdist.com.br',
    phone: '(19) 95432-1098',
  },
  {
    id: 5,
    name: 'Embalagens Ecológicas EcoPack',
    category: 'Descartáveis e Embalagens',
    status: 'HOMOLOGADO',
    contactName: 'Fernanda Lima',
    email: 'f.lima@ecopackembalagens.com',
    phone: '(11) 94321-0987',
  },
]

export const AdminSuppliersPage: React.FC = () => {
  const [suppliers, setSuppliers] = useState<Supplier[]>(INITIAL_SUPPLIERS)
  const [searchTerm, setSearchTerm] = useState('')
  const [showAddModal, setShowAddModal] = useState(false)
  const [newName, setNewName] = useState('')
  const [newCategory, setNewCategory] = useState('Bebidas')
  const [newContact, setNewContact] = useState('')
  const [newEmail, setNewEmail] = useState('')
  const [newPhone, setNewPhone] = useState('')

  const filteredSuppliers = suppliers.filter(
    (s) =>
      s.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.category.toLowerCase().includes(searchTerm.toLowerCase()),
  )

  const handleAddSupplier = (e: React.FormEvent) => {
    e.preventDefault()
    if (!newName.trim() || !newContact.trim() || !newEmail.trim() || !newPhone.trim()) return

    const newSupplier: Supplier = {
      id: suppliers.length + 1,
      name: newName,
      category: newCategory,
      status: 'EM_ANALISE',
      contactName: newContact,
      email: newEmail,
      phone: newPhone,
    }

    setSuppliers([...suppliers, newSupplier])
    setNewName('')
    setNewContact('')
    setNewEmail('')
    setNewPhone('')
    setShowAddModal(false)
  }

  const handleRequestQuote = (supplierName: string) => {
    alert(`Cotação corporativa solicitada com sucesso para o fornecedor: ${supplierName}`)
  }

  return (
    <div className="space-y-6">
      {/* Title & Add button */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black tracking-tight text-white">
            Fornecedores Homologados
          </h1>
          <p className="text-xs font-medium text-gray-400 mt-1">
            Rede de fornecedores oficiais credenciados para atendimento unificado de todas as
            unidades.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowAddModal(true)}
          className="flex items-center justify-center gap-2 bg-brand-500 hover:bg-brand-600 px-4 py-2.5 rounded-xl text-xs font-bold text-white shadow-lg shadow-brand-500/20 transition-all sm:self-center"
        >
          <Plus className="h-4 w-4" />
          Credenciar Fornecedor
        </button>
      </div>

      {/* Filter and stats */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Buscar fornecedores ou insumos..."
            className="w-full bg-gray-950 border border-gray-900 rounded-xl pl-9 pr-4 py-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-brand-500 transition-all"
          />
        </div>
        <span className="text-xs text-gray-400 font-medium">
          Exibindo {filteredSuppliers.length} fornecedores homologados
        </span>
      </div>

      {/* Suppliers Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {filteredSuppliers.map((s) => (
          <div
            key={s.id}
            className="bg-gray-950/40 border border-gray-900/60 rounded-2xl p-5 backdrop-blur-md flex flex-col justify-between shadow-lg hover:border-gray-800 transition-all space-y-4"
          >
            <div className="space-y-2">
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-[9px] font-extrabold uppercase px-2 py-0.5 rounded bg-gray-900 border border-gray-800 text-gray-400">
                    {s.category}
                  </span>
                  <h3 className="text-sm font-bold text-white mt-1.5">{s.name}</h3>
                </div>
                <span
                  className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[9px] font-bold border ${
                    s.status === 'HOMOLOGADO'
                      ? 'bg-green-500/10 border-green-500/20 text-green-400'
                      : s.status === 'EM_ANALISE'
                        ? 'bg-amber-500/10 border-amber-500/20 text-amber-400'
                        : 'bg-red-500/10 border-red-500/20 text-red-400'
                  }`}
                >
                  <ShieldCheck className="h-3 w-3" />
                  {s.status.replace('_', ' ')}
                </span>
              </div>

              {/* Contact info */}
              <div className="pt-2 space-y-1.5 text-xs text-gray-400 font-medium">
                <p className="text-white font-bold text-[11px]">Contato: {s.contactName}</p>
                <div className="flex items-center gap-2">
                  <Mail className="h-3.5 w-3.5 text-gray-500" />
                  <a href={`mailto:${s.email}`} className="hover:text-brand-400 transition-all">
                    {s.email}
                  </a>
                </div>
                <div className="flex items-center gap-2">
                  <Phone className="h-3.5 w-3.5 text-gray-500" />
                  <span>{s.phone}</span>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="pt-4 border-t border-gray-900/40 flex items-center gap-2">
              <button
                type="button"
                onClick={() => handleRequestQuote(s.name)}
                className="flex-1 bg-brand-500/10 hover:bg-brand-500/20 border border-brand-500/30 hover:border-brand-500/40 py-2 rounded-xl text-[10px] font-bold text-brand-400 transition-all"
              >
                Solicitar Cotação
              </button>
              <a
                href="https://google.com"
                target="_blank"
                rel="noreferrer"
                className="bg-gray-900 hover:bg-gray-850 border border-gray-800 p-2 rounded-xl text-gray-400 hover:text-white transition-all"
                title="Acessar Portal do Fornecedor"
              >
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </div>
          </div>
        ))}
      </div>

      {/* Add Modal (Mocked) */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-fade-in">
          <div className="bg-gray-950 border border-gray-900 rounded-2xl max-w-md w-full p-6 space-y-6 shadow-2xl">
            <div>
              <h3 className="text-lg font-black text-white">Credenciar Novo Fornecedor</h3>
              <p className="text-xs text-gray-400 mt-1">
                Insira os dados do fornecedor para análise de homologação corporativa.
              </p>
            </div>

            <form onSubmit={handleAddSupplier} className="space-y-4">
              <div className="space-y-1.5">
                <label
                  htmlFor="supName"
                  className="text-xs font-bold text-gray-400 uppercase tracking-wider"
                >
                  Nome da Empresa
                </label>
                <input
                  id="supName"
                  type="text"
                  required
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="Ex: Frigorífico Central Ltda"
                  className="w-full bg-gray-900 border border-gray-800 rounded-xl px-4 py-3 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-brand-500 transition-all"
                />
              </div>

              <div className="space-y-1.5">
                <label
                  htmlFor="supCat"
                  className="text-xs font-bold text-gray-400 uppercase tracking-wider"
                >
                  Categoria de Insumos
                </label>
                <select
                  id="supCat"
                  value={newCategory}
                  onChange={(e) => setNewCategory(e.target.value)}
                  className="w-full bg-gray-900 border border-gray-800 rounded-xl px-4 py-3 text-xs text-white focus:outline-none focus:border-brand-500 transition-all"
                >
                  <option value="Bebidas">Bebidas e Cervejas</option>
                  <option value="Alimentos">Alimentos e Hortifruti</option>
                  <option value="Equipamentos">Equipamentos e PDV</option>
                  <option value="Embalagens">Descartáveis e Embalagens</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label
                  htmlFor="supContact"
                  className="text-xs font-bold text-gray-400 uppercase tracking-wider"
                >
                  Nome do Contato
                </label>
                <input
                  id="supContact"
                  type="text"
                  required
                  value={newContact}
                  onChange={(e) => setNewContact(e.target.value)}
                  placeholder="Ex: João da Silva"
                  className="w-full bg-gray-900 border border-gray-800 rounded-xl px-4 py-3 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-brand-500 transition-all"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label
                    htmlFor="supEmail"
                    className="text-xs font-bold text-gray-400 uppercase tracking-wider"
                  >
                    E-mail Corporativo
                  </label>
                  <input
                    id="supEmail"
                    type="email"
                    required
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    placeholder="email@fornecedor.com"
                    className="w-full bg-gray-900 border border-gray-800 rounded-xl px-4 py-3 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-brand-500 transition-all"
                  />
                </div>
                <div className="space-y-1.5">
                  <label
                    htmlFor="supPhone"
                    className="text-xs font-bold text-gray-400 uppercase tracking-wider"
                  >
                    Telefone Comercial
                  </label>
                  <input
                    id="supPhone"
                    type="text"
                    required
                    value={newPhone}
                    onChange={(e) => setNewPhone(e.target.value)}
                    placeholder="(11) 99999-9999"
                    className="w-full bg-gray-900 border border-gray-800 rounded-xl px-4 py-3 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-brand-500 transition-all"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="bg-gray-900 hover:bg-gray-850 px-4 py-2.5 rounded-xl text-xs font-bold transition-all"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="bg-brand-500 hover:bg-brand-600 px-4 py-2.5 rounded-xl text-xs font-bold text-white shadow-lg shadow-brand-500/20 transition-all"
                >
                  Enviar para Análise
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
