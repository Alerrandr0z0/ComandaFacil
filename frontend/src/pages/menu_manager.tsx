import {
  ArrowRight,
  Check,
  Edit2,
  Link2,
  Plus,
  Sparkles,
  Star,
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

interface PriceListSummary {
  id: number
  menu_id: number
  name: string
  description: string
  is_active: boolean
  is_active_for_menu: boolean
  valid_from: string
  valid_until: string | null
  items: Array<{ id: number; menu_item_id: number; price: number }>
}

async function fetchCatalogItems(menuItems: MenuItem[]): Promise<MenuItem[]> {
  const res = await httpClient.get<MenuItem[]>('/v1/menu/items')
  const usedIds = new Set(menuItems.map((i) => i.id))
  return res.data.filter((item) => !usedIds.has(item.id))
}

async function linkItemToMenu(menuId: number, itemId: number, category: string): Promise<void> {
  await httpClient.post(`/v1/menu/${menuId}/link-item`, { item_id: itemId, category })
}

async function deleteMenu(
  menuId: number,
  selectedId: number | null,
  onClearSelected: () => void,
  onRefresh: () => void,
): Promise<void> {
  if (!window.confirm('Deseja realmente remover este cardápio permanentemente?')) return
  try {
    await httpClient.delete(`/v1/menu/${menuId}`)
    if (selectedId === menuId) onClearSelected()
    onRefresh()
  } catch (_err) {
    alert('Erro ao remover o cardápio.')
  }
}

// biome-ignore lint/complexity/noExcessiveCognitiveComplexity: page-level component with many states/modals; pre-existing
export default function MenuManagerPage() {
  const [menus, setMenus] = useState<Menu[]>([])
  const [selectedMenuId, setSelectedMenuId] = useState<number | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isCreatingMenu, setIsCreatingMenu] = useState(false)
  const [editingItem, setEditingItem] = useState<MenuItem | null>(null)
  const [editingPriceValue, setEditingPriceValue] = useState('')

  const [basePrices, setBasePrices] = useState<Record<number, number>>({})
  const [priceLists, setPriceLists] = useState<PriceListSummary[]>([])
  const [showPriceDrawer, setShowPriceDrawer] = useState(false)
  const [isCreatingPriceList, setIsCreatingPriceList] = useState(false)
  const [newPriceListName, setNewPriceListName] = useState('')
  const [isLinkingItem, setIsLinkingItem] = useState(false)
  const [catalogItems, setCatalogItems] = useState<MenuItem[]>([])
  const [linkSearchQuery, setLinkSearchQuery] = useState('')
  const [linkCategory, setLinkCategory] = useState('Pratos')

  // Menu form state
  const [newMenuName, setNewMenuName] = useState('')
  const [newMenuDesc, setNewMenuDesc] = useState('')

  const selectedMenu = menus.find((m) => m.id === selectedMenuId) || null

  const fetchPriceLists = useCallback(async () => {
    if (!selectedMenuId) return
    try {
      const res = await httpClient.get<PriceListSummary[]>(`/v1/menu/${selectedMenuId}/price-lists`)
      setPriceLists(res.data)
    } catch (_err) {
      // silent
    }
  }, [selectedMenuId])

  useEffect(() => {
    fetchPriceLists()
  }, [fetchPriceLists])

  const handleActivatePriceList = async (priceListId: number) => {
    if (!selectedMenuId) return
    try {
      await httpClient.put(`/v1/menu/${selectedMenuId}/activate-price-list/${priceListId}`)
      fetchMenus()
      fetchPriceLists()
    } catch (_err) {
      alert('Erro ao ativar lista de preços.')
    }
  }

  const handleCreatePriceList = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedMenuId || !newPriceListName.trim()) return
    const plId = Math.floor(Math.random() * 1000000000)
    try {
      await httpClient.post(`/v1/menu/${selectedMenuId}/price-lists`, {
        id: plId,
        name: newPriceListName,
      })
      setNewPriceListName('')
      setIsCreatingPriceList(false)
      fetchPriceLists()
    } catch (_err) {
      alert('Erro ao criar lista de preços.')
    }
  }

  const fetchBasePrices = useCallback(async () => {
    try {
      const res = await httpClient.get<MenuItem[]>('/v1/menu/items')
      const map: Record<number, number> = {}
      for (const item of res.data) {
        map[item.id] = Number(item.price ?? 0)
      }
      setBasePrices(map)
    } catch (_err) {
      // silent — fallback to resolved price
    }
  }, [])

  const fetchMenus = useCallback(async () => {
    setIsLoading(true)
    try {
      const res = await httpClient.get<Menu[]>('/v1/menu')
      setMenus(res.data)
    } catch (_err) {
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchMenus()
    fetchBasePrices()
  }, [fetchMenus, fetchBasePrices])

  const handleCreateMenu = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newMenuName.trim()) return

    const newId = Math.floor(Math.random() * 1000000000)
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

  const handleDeleteMenu = (menuId: number) =>
    deleteMenu(menuId, selectedMenuId, () => setSelectedMenuId(null), fetchMenus)

  const handleDeleteItem = async (itemId: number) => {
    if (!selectedMenu || !window.confirm('Deseja remover este prato do cardápio?')) return
    try {
      await httpClient.delete(`/v1/menu/${selectedMenu.id}/items/${itemId}`)
      fetchMenus()
    } catch (_err) {
      alert('Erro ao remover o item.')
    }
  }

  const getBasePrice = (itemId: number): number | undefined => basePrices[itemId]

  const hasOverridePrice = (item: MenuItem): boolean => {
    const base = getBasePrice(item.id)
    if (base === undefined) return false
    return (
      item.price !== undefined && item.price !== null && Math.abs(Number(item.price) - base) > 0.001
    )
  }

  const getItemPrice = (item: MenuItem): number => {
    if (item.price !== undefined && item.price !== null) {
      return Number(item.price)
    }
    return getBasePrice(item.id) ?? 0
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
      fetchBasePrices()
    } catch (_err) {
      alert('Erro ao atualizar o preço do item.')
    }
  }

  const handleClearPrice = async () => {
    if (!selectedMenu || !editingItem) return
    if (
      !window.confirm(
        `Remover o preço especial de "${editingItem.name}"? O valor voltará ao preço base do catálogo.`,
      )
    )
      return
    try {
      await httpClient.delete(`/v1/menu/${selectedMenu.id}/items/${editingItem.id}/price`)
      setEditingItem(null)
      setEditingPriceValue('')
      fetchMenus()
      fetchBasePrices()
    } catch (_err) {
      alert('Erro ao remover o preço especial.')
    }
  }

  const handleOpenLink = async () => {
    if (!selectedMenu) return
    try {
      const items = await fetchCatalogItems(selectedMenu.items)
      setCatalogItems(items)
      setIsLinkingItem(true)
      setLinkSearchQuery('')
      setLinkCategory('Pratos')
    } catch (_err) {
      alert('Erro ao carregar itens do catálogo.')
    }
  }

  const handleLinkItem = async (item: MenuItem) => {
    if (!selectedMenu) return
    try {
      await linkItemToMenu(selectedMenu.id, item.id, linkCategory)
      setIsLinkingItem(false)
      fetchMenus()
    } catch (_err) {
      alert('Erro ao vincular item ao cardápio.')
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
              Organize quais produtos compõem cada cardápio
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
                    onClick={() => setSelectedMenuId(menu.id)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        setSelectedMenuId(menu.id)
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
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        setShowPriceDrawer(true)
                        fetchPriceLists()
                      }}
                      className="rounded-lg bg-gray-900 px-3 py-1.5 text-xs font-bold text-amber-400 border border-amber-500/10 hover:border-amber-500/25 transition flex items-center gap-1"
                    >
                      <Star className="h-3.5 w-3.5" />
                      Preços Especiais
                      {priceLists.length > 0 && (
                        <span className="ml-0.5 text-[9px] bg-amber-500/15 border border-amber-500/20 px-1.5 py-0.5 rounded-full">
                          {priceLists.length}
                        </span>
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={handleOpenLink}
                      className="rounded-lg bg-gray-900 px-3 py-1.5 text-xs font-bold text-emerald-400 border border-emerald-500/10 hover:border-emerald-500/20 transition flex items-center gap-1"
                    >
                      <Link2 className="h-3.5 w-3.5" />
                      Vincular Existente
                    </button>
                  </div>
                </div>

                {selectedMenu.items.length === 0 ? (
                  <div className="py-20 text-center space-y-3">
                    <p className="text-xs text-gray-500 italic">
                      Nenhum item vinculado a este cardápio.
                    </p>
                    <button
                      type="button"
                      onClick={handleOpenLink}
                      className="mx-auto rounded-lg bg-gray-900 px-3 py-1.5 text-[10px] font-bold text-emerald-400 border border-emerald-500/10 hover:bg-gray-850 transition"
                    >
                      Vincular Item do Catálogo
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
                          <h5 className="text-xs font-bold text-gray-200 truncate flex items-center gap-1.5">
                            {item.name}
                            {hasOverridePrice(item) && (
                              <span className="text-[8px] font-extrabold uppercase text-brand-400 px-1 py-0.5 rounded-full bg-brand-500/10 border border-brand-500/20">
                                Preço Especial
                              </span>
                            )}
                          </h5>
                          <p className="text-[10px] text-gray-550 mt-0.5 line-clamp-1">
                            {item.description || 'Sem descrição.'}
                          </p>
                          <div className="flex items-center gap-2 mt-2">
                            <span className="text-[9px] uppercase font-bold text-brand-400 px-1.5 py-0.5 rounded bg-brand-500/5 border border-brand-500/10">
                              {item.category}
                            </span>
                            <div className="flex items-center gap-1.5">
                              {hasOverridePrice(item) ? (
                                <div className="flex items-center gap-1 text-[10px]">
                                  <span className="text-gray-600 line-through">
                                    R$ {getBasePrice(item.id)?.toFixed(2)}
                                  </span>
                                  <span className="text-xs font-black text-amber-500">
                                    R$ {getItemPrice(item).toFixed(2)}
                                  </span>
                                </div>
                              ) : (
                                <span className="text-xs font-black text-amber-500">
                                  R$ {getItemPrice(item).toFixed(2)}
                                </span>
                              )}
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
                          title="Desvincular Prato"
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

        {/* Price Lists Drawer */}
        {showPriceDrawer && selectedMenu && (
          <>
            {/* Backdrop */}
            {/* biome-ignore lint/a11y/noStaticElementInteractions: backdrop is a presentation dismiss target */}
            <div
              role="presentation"
              className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
              onClick={() => {
                setShowPriceDrawer(false)
                setIsCreatingPriceList(false)
                setNewPriceListName('')
              }}
            />
            {/* Drawer panel */}
            <aside className="fixed right-0 top-0 z-50 h-full w-full max-w-sm border-l border-gray-900 bg-[#07070f] shadow-2xl flex flex-col animate-slide-in-right">
              {/* Drawer header */}
              <div className="flex items-center justify-between px-5 py-4 border-b border-gray-900/60">
                <div>
                  <h3 className="text-sm font-black text-white uppercase tracking-wide flex items-center gap-2">
                    <Star className="h-4 w-4 text-amber-400" />
                    Preços Especiais
                  </h3>
                  <p className="text-[10px] text-gray-500 mt-0.5 font-medium">
                    {selectedMenu.name}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setShowPriceDrawer(false)
                    setIsCreatingPriceList(false)
                    setNewPriceListName('')
                  }}
                  className="rounded-lg p-2 border border-gray-800 text-gray-400 hover:text-white hover:bg-white/[0.03] transition"
                  aria-label="Fechar painel"
                >
                  ✕
                </button>
              </div>

              {/* Drawer body */}
              <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
                {priceLists.length === 0 && !isCreatingPriceList ? (
                  <div className="flex flex-col items-center justify-center py-16 space-y-4 text-center">
                    <div className="h-12 w-12 rounded-2xl bg-amber-500/5 border border-amber-500/10 flex items-center justify-center">
                      <Star className="h-5 w-5 text-amber-500/40" />
                    </div>
                    <div>
                      <p className="text-xs font-bold text-gray-400">Nenhuma lista de preços</p>
                      <p className="text-[10px] text-gray-600 mt-1 max-w-[200px]">
                        Crie listas para promoções, happy hour ou fins de semana
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setIsCreatingPriceList(true)}
                      className="rounded-xl bg-brand-500 hover:bg-brand-600 px-4 py-2 text-xs font-bold text-white transition"
                    >
                      Criar Primeira Lista
                    </button>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {priceLists.map((pl) => (
                      <div
                        key={pl.id}
                        className={`p-3.5 rounded-xl border transition ${
                          pl.is_active_for_menu
                            ? 'border-amber-500/30 bg-amber-950/10'
                            : 'border-gray-900/60 bg-gray-950/20 hover:border-gray-800'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2 min-w-0">
                            {pl.is_active_for_menu ? (
                              <Check className="h-3.5 w-3.5 text-amber-400 shrink-0" />
                            ) : (
                              <div className="h-3.5 w-3.5 rounded-full border border-gray-700 shrink-0" />
                            )}
                            <div className="min-w-0">
                              <span className="text-xs font-bold text-gray-200 truncate block">
                                {pl.name}
                              </span>
                              {pl.is_active_for_menu && (
                                <span className="text-[8px] font-extrabold uppercase text-amber-400">
                                  Ativo
                                </span>
                              )}
                            </div>
                          </div>
                          <div className="flex items-center gap-2 shrink-0">
                            <span className="text-[9px] text-gray-600">
                              {pl.items.length} item{pl.items.length !== 1 ? 'ns' : ''}
                            </span>
                            {!pl.is_active_for_menu && (
                              <button
                                type="button"
                                onClick={() => handleActivatePriceList(pl.id)}
                                className="text-[9px] font-bold text-brand-400 hover:text-brand-300 px-2 py-1 rounded border border-gray-800 hover:border-brand-500/30 transition"
                              >
                                Ativar
                              </button>
                            )}
                          </div>
                        </div>
                        {pl.valid_until && (
                          <p className="text-[9px] text-gray-600 mt-1.5 ml-5">
                            Válido até {new Date(pl.valid_until).toLocaleDateString('pt-BR')}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Drawer footer */}
              <div className="px-5 py-4 border-t border-gray-900/60">
                {isCreatingPriceList ? (
                  <form onSubmit={handleCreatePriceList} className="space-y-3">
                    <div className="space-y-1.5">
                      <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                        Nome da Lista
                      </span>
                      <input
                        type="text"
                        required
                        placeholder="Ex: Happy Hour, Fim de Semana..."
                        value={newPriceListName}
                        onChange={(e) => setNewPriceListName(e.target.value)}
                        className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
                      />
                    </div>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => {
                          setIsCreatingPriceList(false)
                          setNewPriceListName('')
                        }}
                        className="flex-1 rounded-xl border border-gray-850 py-2.5 text-xs font-bold text-gray-400 hover:bg-white/[0.02] transition"
                      >
                        Cancelar
                      </button>
                      <button
                        type="submit"
                        className="flex-1 rounded-xl bg-brand-500 hover:bg-brand-600 py-2.5 text-xs font-bold text-white transition"
                      >
                        Criar Lista
                      </button>
                    </div>
                  </form>
                ) : (
                  <button
                    type="button"
                    onClick={() => setIsCreatingPriceList(true)}
                    className="w-full rounded-xl border border-dashed border-gray-800 hover:border-amber-500/20 hover:text-amber-400 py-2.5 text-xs font-bold text-gray-500 transition flex items-center justify-center gap-1.5"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    Nova Lista de Preços
                  </button>
                )}
              </div>
            </aside>
          </>
        )}

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

        {/* Modal: Edit Item Price */}
        {editingItem && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
            <form
              onSubmit={handleEditPrice}
              className="w-full max-w-sm rounded-2xl glass-elevated p-6 space-y-4"
            >
              <div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                  Preço Especial
                </h3>
                <p className="text-xs text-gray-550 mt-1">
                  Defina um preço especial para <strong>{editingItem.name}</strong> neste cardápio.
                </p>
                {getBasePrice(editingItem.id) !== undefined && (
                  <p className="text-[10px] text-gray-600 mt-1">
                    Preço base no catálogo:{' '}
                    <span className="font-bold text-gray-400">
                      R$ {getBasePrice(editingItem.id)?.toFixed(2)}
                    </span>
                  </p>
                )}
              </div>

              <div className="space-y-1.5">
                <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                  Preço Especial (R$)
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

              {hasOverridePrice(editingItem) && (
                <div className="border-t border-gray-900 pt-3">
                  <button
                    type="button"
                    onClick={handleClearPrice}
                    className="w-full rounded-xl border border-rose-500/20 hover:bg-rose-950/10 py-2 text-xs font-bold text-rose-400 transition"
                  >
                    Remover Preço Especial
                  </button>
                </div>
              )}
            </form>
          </div>
        )}

        {/* Modal: Link Existing Item */}
        {isLinkingItem && selectedMenu && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
            <div className="w-full max-w-lg rounded-2xl glass-elevated p-6 space-y-4 max-h-[90vh] overflow-y-auto">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <Link2 className="h-4 w-4 text-emerald-400" />
                    Vincular Item Existente
                  </h3>
                  <p className="text-[10px] text-gray-500 font-medium mt-0.5">
                    Selecione um item do catálogo para vincular a {selectedMenu.name}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setIsLinkingItem(false)}
                  className="rounded-lg border border-gray-800 hover:bg-white/[0.03] px-3 py-1.5 text-[10px] font-bold text-gray-400 transition"
                >
                  Fechar
                </button>
              </div>

              {catalogItems.length === 0 ? (
                <div className="border border-dashed border-gray-850 rounded-xl p-8 text-center">
                  <p className="text-xs text-gray-500 italic">
                    Todos os itens do catálogo já estão vinculados a este cardápio.
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  <input
                    type="text"
                    placeholder="Buscar item no catálogo..."
                    value={linkSearchQuery}
                    onChange={(e) => setLinkSearchQuery(e.target.value)}
                    className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
                  />

                  <div className="space-y-1.5">
                    <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                      Vincular como categoria
                    </span>
                    <select
                      value={linkCategory}
                      onChange={(e) => setLinkCategory(e.target.value)}
                      className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input bg-[#0b0b11]"
                    >
                      <option value="Entradas">Entradas</option>
                      <option value="Pratos">Pratos</option>
                      <option value="Bebidas">Bebidas</option>
                      <option value="Bebidas Alcoólicas">Bebidas Alcoólicas</option>
                      <option value="Sobremesas">Sobremesas</option>
                    </select>
                  </div>

                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {catalogItems
                      .filter(
                        (item) =>
                          !linkSearchQuery ||
                          item.name.toLowerCase().includes(linkSearchQuery.toLowerCase()),
                      )
                      .map((item) => (
                        <button
                          key={item.id}
                          type="button"
                          onClick={() => handleLinkItem(item)}
                          className="w-full flex items-center gap-3 p-3 rounded-xl border border-gray-900/60 bg-gray-950/20 hover:bg-white/[0.02] text-left transition"
                        >
                          {item.image_url ? (
                            <img
                              src={item.image_url}
                              alt={item.name}
                              className="w-10 h-10 rounded-lg object-cover bg-gray-900 border border-gray-850"
                            />
                          ) : (
                            <div className="w-10 h-10 rounded-lg bg-gray-900 border border-gray-850 flex items-center justify-center text-gray-600">
                              <Sparkles className="h-4 w-4" />
                            </div>
                          )}
                          <div className="flex-1 min-w-0">
                            <span className="text-xs font-bold text-gray-200 truncate block">
                              {item.name}
                            </span>
                            <span className="text-[9px] text-gray-500">
                              {item.description || 'Sem descrição.'}
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-[9px] uppercase font-bold text-brand-400 px-1.5 py-0.5 rounded bg-brand-500/5 border border-brand-500/10">
                              {item.category}
                            </span>
                            <span className="text-[10px] font-bold text-amber-500">
                              R$ {Number(item.price ?? 0).toFixed(2)}
                            </span>
                          </div>
                        </button>
                      ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}
