import {
  ArrowRight,
  Edit2,
  Plus,
  Sparkles,
  ToggleLeft,
  ToggleRight,
  Trash2,
  Utensils,
} from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import Layout from '@/shared/components/layout'
import { httpClient } from '@/shared/lib/http_client'

interface MenuItem {
  id: number
  name: string
  description: string
  category: string
  price?: number
  image_url: string | null
  is_available: boolean
}

interface Menu {
  id: number
  name: string
  description: string
  is_active: boolean
  items: MenuItem[]
}

export default function MenuManagerPage() {
  const [menus, setMenus] = useState<Menu[]>([])
  const [selectedMenu, setSelectedMenu] = useState<Menu | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isCreatingMenu, setIsCreatingMenu] = useState(false)
  const [isAddingItem, setIsAddingItem] = useState(false)
  const [editingItem, setEditingItem] = useState<MenuItem | null>(null)
  const [editingPriceValue, setEditingPriceValue] = useState('')

  // Menu form state
  const [newMenuName, setNewMenuName] = useState('')
  const [newMenuDesc, setNewMenuDesc] = useState('')

  // Item form state
  const [newItemName, setNewItemName] = useState('')
  const [newItemDesc, setNewItemDesc] = useState('')
  const [newItemCategory, setNewItemCategory] = useState('Pratos')
  const [newItemPrice, setNewItemPrice] = useState('25.90')
  const [newItemImageUrl, setNewItemImageUrl] = useState('')

  const fetchMenus = useCallback(async () => {
    setIsLoading(true)
    try {
      const res = await httpClient.get<Menu[]>('/v1/menu')
      setMenus(res.data)
      if (selectedMenu) {
        const updated = res.data.find((m) => m.id === selectedMenu.id)
        if (updated) setSelectedMenu(updated)
      }
    } catch (_err) {
    } finally {
      setIsLoading(false)
    }
  }, [selectedMenu])

  useEffect(() => {
    fetchMenus()
  }, [fetchMenus])

  const handleCreateMenu = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newMenuName.trim()) return

    const newId = Date.now() + Math.floor(Math.random() * 1000)
    try {
      await httpClient.post('/v1/menu', {
        id: newId,
        name: newMenuName,
        description: newMenuDesc,
      })
      setNewMenuName('')
      setNewMenuDesc('')
      setIsCreatingMenu(false)
      fetchMenus()
    } catch (_err) {
      alert('Falha ao criar o cardápio. Verifique os dados.')
    }
  }

  const handleToggleMenu = async (menuId: number, currentActive: boolean) => {
    try {
      await httpClient.patch(`/v1/menu/${menuId}/toggle`, {
        activate: !currentActive,
      })
      fetchMenus()
    } catch (_err) {
      alert('Erro ao alterar o status do cardápio.')
    }
  }

  const handleDeleteMenu = async (menuId: number) => {
    if (!window.confirm('Deseja realmente remover este cardápio permanentemente?')) return
    try {
      await httpClient.delete(`/v1/menu/${menuId}`)
      if (selectedMenu?.id === menuId) setSelectedMenu(null)
      fetchMenus()
    } catch (_err) {
      alert('Erro ao remover o cardápio.')
    }
  }

  const handleAddItem = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedMenu || !newItemName.trim() || !newItemCategory.trim()) return

    const newId = Date.now() + Math.floor(Math.random() * 1000)
    const priceNum = parseFloat(newItemPrice)

    try {
      await httpClient.post(`/v1/menu/${selectedMenu.id}/items`, {
        id: newId,
        name: newItemName,
        description: newItemDesc,
        category: newItemCategory,
        image_url: newItemImageUrl.trim() || null,
        is_available: true,
      })

      // Store custom price locally
      if (!Number.isNaN(priceNum) && priceNum >= 0) {
        const pricesStr = localStorage.getItem('cf_menu_item_prices') || '{}'
        const prices = JSON.parse(pricesStr)
        prices[newId] = priceNum
        localStorage.setItem('cf_menu_item_prices', JSON.stringify(prices))
      }

      setNewItemName('')
      setNewItemDesc('')
      setNewItemCategory('Pratos')
      setNewItemPrice('25.90')
      setNewItemImageUrl('')
      setIsAddingItem(false)
      fetchMenus()
    } catch (_err) {
      alert('Erro ao adicionar o prato.')
    }
  }

  const handleDeleteItem = async (itemId: number) => {
    if (!selectedMenu || !window.confirm('Deseja remover este prato do cardápio?')) return
    try {
      await httpClient.delete(`/v1/menu/${selectedMenu.id}/items/${itemId}`)
      fetchMenus()
    } catch (_err) {
      alert('Erro ao remover o item.')
    }
  }

  const getItemPrice = (item: MenuItem): number => {
    if (item.price !== undefined && item.price !== null) {
      return Number(item.price)
    }
    const base = 12.0
    const offset = (item.id % 6) * 5.5
    return base + offset
  }

  const handleEditPrice = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedMenu || !editingItem) return
    const priceNum = parseFloat(editingPriceValue)
    if (Number.isNaN(priceNum) || priceNum < 0) {
      alert('Por favor, insira um preço válido.')
      return
    }

    try {
      await httpClient.patch(`/v1/menu/${selectedMenu.id}/items/${editingItem.id}/price`, {
        price: priceNum,
      })
      setEditingItem(null)
      setEditingPriceValue('')
      fetchMenus()
    } catch (_err) {
      alert('Erro ao atualizar o preço do item.')
    }
  }

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-center justify-between border-b border-gray-900/60 pb-3">
          <div>
            <h2 className="text-lg font-black text-white tracking-wide uppercase flex items-center gap-2">
              <Utensils className="h-5 w-5 text-brand-400" />
              Gestão de Cardápios
            </h2>
            <p className="text-xs text-gray-550 font-medium mt-0.5">
              Crie cardápios dinâmicos e gerencie a oferta de produtos da sua franquia
            </p>
          </div>
          <button
            type="button"
            onClick={() => setIsCreatingMenu(true)}
            className="rounded-xl bg-brand-500 hover:bg-brand-600 px-4 py-2 text-xs font-bold text-white transition flex items-center gap-1.5"
          >
            <Plus className="h-4 w-4" />
            Novo Cardápio
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Menu selection list column */}
          <div className="lg:col-span-1 space-y-4">
            <h3 className="text-xs font-extrabold uppercase tracking-wider text-gray-500">
              Seus Cardápios
            </h3>

            {isLoading && menus.length === 0 ? (
              <div className="h-32 rounded-2xl border border-gray-900 bg-gray-950/20 animate-pulse flex items-center justify-center text-xs text-gray-500 italic">
                Buscando cardápios do servidor...
              </div>
            ) : menus.length === 0 ? (
              <div className="border border-dashed border-gray-850 rounded-2xl p-6 text-center space-y-3">
                <p className="text-xs text-gray-500 italic">Nenhum cardápio cadastrado.</p>
                <button
                  type="button"
                  onClick={() => setIsCreatingMenu(true)}
                  className="mx-auto rounded-lg bg-gray-900 px-3 py-1.5 text-[10px] font-bold text-brand-400 border border-brand-500/10 hover:bg-gray-850 transition"
                >
                  Criar Primeiro Cardápio
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                {menus.map((menu) => (
                  // biome-ignore lint/a11y/useSemanticElements: custom card container requires interactive div
                  <div
                    key={menu.id}
                    onClick={() => setSelectedMenu(menu)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        setSelectedMenu(menu)
                      }
                    }}
                    role="button"
                    tabIndex={0}
                    className={`p-4 rounded-2xl border transition-all duration-300 cursor-pointer relative group ${
                      selectedMenu?.id === menu.id
                        ? 'border-brand-500 bg-brand-950/5'
                        : 'border-gray-900/60 bg-gray-950/15 hover:border-gray-800'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <h4 className="text-xs font-bold text-gray-200">{menu.name}</h4>
                        <p className="text-[10px] text-gray-500 mt-1 max-w-[200px] line-clamp-1">
                          {menu.description || 'Sem descrição.'}
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleToggleMenu(menu.id, menu.is_active)
                        }}
                        className="text-gray-400 hover:text-white transition"
                        title={menu.is_active ? 'Desativar Cardápio' : 'Ativar Cardápio'}
                      >
                        {menu.is_active ? (
                          <ToggleRight className="h-5 w-5 text-emerald-400" />
                        ) : (
                          <ToggleLeft className="h-5 w-5 text-gray-600" />
                        )}
                      </button>
                    </div>

                    <div className="mt-4 pt-3 border-t border-gray-900/40 flex justify-between items-center text-[10px]">
                      <span className="text-gray-500 font-bold uppercase tracking-wider">
                        {menu.items.length} itens
                      </span>
                      <div className="flex gap-2.5 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation()
                            handleDeleteMenu(menu.id)
                          }}
                          className="text-rose-500 hover:text-rose-400 p-1"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                        <span className="text-brand-400 font-bold flex items-center gap-0.5">
                          Itens <ArrowRight className="h-3 w-3" />
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Menu items detail column */}
          <div className="lg:col-span-2 space-y-4">
            {selectedMenu ? (
              <div className="border border-gray-900/60 rounded-2xl bg-gray-950/10 p-5 backdrop-blur-md glass-card space-y-4 min-h-[400px]">
                <div className="flex items-center justify-between border-b border-gray-900 pb-3">
                  <div>
                    <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
                      {selectedMenu.name}
                      <span
                        className={`text-[9px] px-2 py-0.5 rounded-full border uppercase tracking-wider font-extrabold ${
                          selectedMenu.is_active
                            ? 'border-emerald-500/20 bg-emerald-950/10 text-emerald-400'
                            : 'border-gray-800 bg-gray-900 text-gray-500'
                        }`}
                      >
                        {selectedMenu.is_active ? 'Ativo' : 'Inativo'}
                      </span>
                    </h3>
                    <p className="text-xs text-gray-550 mt-0.5">
                      {selectedMenu.description || 'Sem descrição cadastrada.'}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setIsAddingItem(true)}
                    className="rounded-lg bg-gray-900 px-3 py-1.5 text-xs font-bold text-brand-400 border border-brand-500/10 hover:border-brand-500/20 transition flex items-center gap-1"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    Adicionar Prato
                  </button>
                </div>

                {selectedMenu.items.length === 0 ? (
                  <div className="py-20 text-center space-y-3">
                    <p className="text-xs text-gray-500 italic">
                      Nenhum item cadastrado neste cardápio.
                    </p>
                    <button
                      type="button"
                      onClick={() => setIsAddingItem(true)}
                      className="mx-auto rounded-lg bg-gray-900 px-3 py-1.5 text-[10px] font-bold text-brand-400 border border-brand-500/10 hover:bg-gray-850 transition"
                    >
                      Adicionar Primeiro Prato
                    </button>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {selectedMenu.items.map((item) => (
                      <div
                        key={item.id}
                        className="p-3.5 rounded-xl border border-gray-900/60 bg-gray-950/20 flex gap-3 relative group"
                      >
                        {item.image_url ? (
                          <img
                            src={item.image_url}
                            alt={item.name}
                            className="w-12 h-12 rounded-lg object-cover bg-gray-900 border border-gray-850"
                          />
                        ) : (
                          <div className="w-12 h-12 rounded-lg bg-gray-900 border border-gray-850 flex items-center justify-center text-gray-600">
                            <Sparkles className="h-5 w-5" />
                          </div>
                        )}

                        <div className="flex-1 min-w-0 pr-6">
                          <h5 className="text-xs font-bold text-gray-200 truncate">{item.name}</h5>
                          <p className="text-[10px] text-gray-550 mt-0.5 line-clamp-1">
                            {item.description || 'Sem descrição.'}
                          </p>
                          <div className="flex items-center gap-2 mt-2">
                            <span className="text-[9px] uppercase font-bold text-brand-400 px-1.5 py-0.5 rounded bg-brand-500/5 border border-brand-500/10">
                              {item.category}
                            </span>
                            <div className="flex items-center gap-1.5">
                              <span className="text-xs font-black text-amber-500">
                                R$ {getItemPrice(item).toFixed(2)}
                              </span>
                              <button
                                type="button"
                                onClick={() => {
                                  setEditingItem(item)
                                  setEditingPriceValue(getItemPrice(item).toFixed(2))
                                }}
                                className="text-gray-650 hover:text-brand-400 p-0.5 rounded transition"
                                title="Alterar Preço"
                              >
                                <Edit2 className="h-3 w-3" />
                              </button>
                            </div>
                          </div>
                        </div>

                        <button
                          type="button"
                          onClick={() => handleDeleteItem(item.id)}
                          className="absolute right-3 bottom-3 text-gray-600 hover:text-rose-500 opacity-0 group-hover:opacity-100 transition-all p-1"
                          title="Remover Prato"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="border border-dashed border-gray-850 rounded-2xl p-12 text-center text-xs text-gray-500 italic min-h-[400px] flex items-center justify-center">
                Selecione um cardápio ao lado para gerenciar seus itens.
              </div>
            )}
          </div>
        </div>

        {/* Modal: Create Menu */}
        {isCreatingMenu && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
            <form
              onSubmit={handleCreateMenu}
              className="w-full max-w-sm rounded-2xl glass-elevated p-6 space-y-4"
            >
              <div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                  Criar Novo Cardápio
                </h3>
                <p className="text-xs text-gray-550 mt-1">
                  Defina o nome e descrição do seu cardápio
                </p>
              </div>

              <div className="space-y-3">
                <div className="space-y-1.5">
                  <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                    Nome do Cardápio
                  </span>
                  <input
                    type="text"
                    required
                    placeholder="Ex: Almoço Executivo, Happy Hour"
                    value={newMenuName}
                    onChange={(e) => setNewMenuName(e.target.value)}
                    className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
                  />
                </div>

                <div className="space-y-1.5">
                  <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                    Descrição (Opcional)
                  </span>
                  <textarea
                    placeholder="Ex: Servido de segunda a sexta-feira das 11h às 15h"
                    value={newMenuDesc}
                    onChange={(e) => setNewMenuDesc(e.target.value)}
                    className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input min-h-[80px]"
                  />
                </div>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsCreatingMenu(false)}
                  className="flex-1 rounded-xl border border-gray-850 hover:bg-white/[0.02] py-2.5 text-xs font-bold text-gray-400 transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="flex-1 rounded-xl bg-brand-500 hover:bg-brand-600 py-2.5 text-xs font-bold text-white transition"
                >
                  Criar Cardápio
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Modal: Add Menu Item */}
        {isAddingItem && selectedMenu && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
            <form
              onSubmit={handleAddItem}
              className="w-full max-w-sm rounded-2xl glass-elevated p-6 space-y-4"
            >
              <div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                  Adicionar Item a {selectedMenu.name}
                </h3>
                <p className="text-xs text-gray-550 mt-1">Insira os detalhes do prato ou bebida</p>
              </div>

              <div className="space-y-3">
                <div className="space-y-1.5">
                  <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                    Nome do Item
                  </span>
                  <input
                    type="text"
                    required
                    placeholder="Ex: Filé Mignon Grelhado"
                    value={newItemName}
                    onChange={(e) => setNewItemName(e.target.value)}
                    className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
                  />
                </div>

                <div className="space-y-1.5">
                  <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                    Descrição do Item
                  </span>
                  <input
                    type="text"
                    placeholder="Ex: Acompanha arroz, batatas e farofa"
                    value={newItemDesc}
                    onChange={(e) => setNewItemDesc(e.target.value)}
                    className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                      Categoria
                    </span>
                    <select
                      value={newItemCategory}
                      onChange={(e) => setNewItemCategory(e.target.value)}
                      className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input bg-[#0b0b11]"
                    >
                      <option value="Entradas">Entradas</option>
                      <option value="Pratos">Pratos</option>
                      <option value="Bebidas">Bebidas</option>
                      <option value="Bebidas Alcoólicas">Bebidas Alcoólicas</option>
                      <option value="Sobremesas">Sobremesas</option>
                    </select>
                  </div>

                  <div className="space-y-1.5">
                    <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                      Preço (R$)
                    </span>
                    <input
                      type="number"
                      step="0.01"
                      required
                      placeholder="29.90"
                      value={newItemPrice}
                      onChange={(e) => setNewItemPrice(e.target.value)}
                      className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                    URL da Imagem (Opcional)
                  </span>
                  <input
                    type="url"
                    placeholder="Ex: https://imagens.com/prato.jpg"
                    value={newItemImageUrl}
                    onChange={(e) => setNewItemImageUrl(e.target.value)}
                    className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
                  />
                </div>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsAddingItem(false)}
                  className="flex-1 rounded-xl border border-gray-850 hover:bg-white/[0.02] py-2.5 text-xs font-bold text-gray-400 transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="flex-1 rounded-xl bg-brand-500 hover:bg-brand-600 py-2.5 text-xs font-bold text-white transition"
                >
                  Adicionar Item
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Modal: Edit Item Price */}
        {editingItem && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
            <form
              onSubmit={handleEditPrice}
              className="w-full max-w-sm rounded-2xl glass-elevated p-6 space-y-4"
            >
              <div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                  Alterar Preço do Item
                </h3>
                <p className="text-xs text-gray-550 mt-1">
                  Defina o novo preço para <strong>{editingItem.name}</strong> no cardápio ativo.
                </p>
              </div>

              <div className="space-y-1.5">
                <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                  Preço (R$)
                </span>
                <input
                  type="number"
                  step="0.01"
                  required
                  placeholder="29.90"
                  value={editingPriceValue}
                  onChange={(e) => setEditingPriceValue(e.target.value)}
                  className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setEditingItem(null)
                    setEditingPriceValue('')
                  }}
                  className="flex-1 rounded-xl border border-gray-850 hover:bg-white/[0.02] py-2.5 text-xs font-bold text-gray-400 transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="flex-1 rounded-xl bg-brand-500 hover:bg-brand-600 py-2.5 text-xs font-bold text-white transition"
                >
                  Salvar Preço
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
    </Layout>
  )
}
