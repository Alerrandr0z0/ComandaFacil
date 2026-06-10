import { BookOpen, Plus, Search, Sparkles, Trash2, Utensils, X } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import RecipeManager from '@/features/stock/components/recipe_manager'
import { httpClient } from '@/shared/lib/http_client'

interface CatalogItem {
  id: number
  name: string
  description: string
  category: string
  price: number | null
  image_url: string | null
  is_available: boolean
  station_type: string
  preparation_profile: string
}

const EMPTY_FORM = {
  name: '',
  description: '',
  category: 'Pratos',
  base_price: '25.90',
  image_url: '',
  station_type: 'GRILL',
  is_available: true,
  preparation_profile: 'STANDARD',
}

export default function CatalogManager() {
  const [items, setItems] = useState<CatalogItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [editingItem, setEditingItem] = useState<CatalogItem | null>(null)
  const [recipeItem, setRecipeItem] = useState<CatalogItem | null>(null)
  const [form, setForm] = useState(EMPTY_FORM)

  const fetchItems = useCallback(async () => {
    setIsLoading(true)
    try {
      const res = await httpClient.get<CatalogItem[]>('/v1/menu/items')
      setItems(res.data)
    } catch (_err) {
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchItems()
  }, [fetchItems])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.name.trim()) return

    const newId = Math.floor(Math.random() * 1000000000)
    try {
      await httpClient.post('/v1/menu/items', {
        id: newId,
        name: form.name,
        description: form.description,
        category: form.category,
        base_price: parseFloat(form.base_price) || 0,
        station_type:
          form.category === 'Bebidas' || form.category === 'Bebidas Alcoólicas'
            ? 'BEVERAGE'
            : form.station_type,
        image_url: form.image_url.trim() || null,
        is_available: form.is_available,
        preparation_profile: form.preparation_profile,
      })
      setForm(EMPTY_FORM)
      setIsCreating(false)
      fetchItems()
    } catch (_err) {
      alert('Falha ao criar o item.')
    }
  }

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editingItem || !form.name.trim()) return

    try {
      await httpClient.patch(`/v1/menu/items/${editingItem.id}`, {
        name: form.name,
        description: form.description,
        category: form.category,
        base_price: parseFloat(form.base_price) || 0,
        station_type:
          form.category === 'Bebidas' || form.category === 'Bebidas Alcoólicas'
            ? 'BEVERAGE'
            : form.station_type,
        image_url: form.image_url.trim() || null,
        is_available: form.is_available,
      })
      setEditingItem(null)
      setForm(EMPTY_FORM)
      fetchItems()
    } catch (_err) {
      alert('Falha ao atualizar o item.')
    }
  }

  const handleDelete = async (item: CatalogItem) => {
    if (!window.confirm(`Deseja excluir "${item.name}" permanentemente?`)) return
    try {
      await httpClient.delete(`/v1/menu/items/${item.id}`)
      fetchItems()
    } catch (_err) {
      alert('Erro ao excluir o item.')
    }
  }

  const handleToggleAvailability = async (item: CatalogItem) => {
    try {
      await httpClient.patch(`/v1/menu/items/${item.id}`, {
        name: item.name,
        description: item.description,
        category: item.category,
        base_price: Number(item.price ?? 0),
        station_type: item.station_type,
        image_url: item.image_url,
        is_available: !item.is_available,
      })
      fetchItems()
    } catch (_err) {
      alert('Erro ao alterar disponibilidade.')
    }
  }

  const openEdit = (item: CatalogItem) => {
    setEditingItem(item)
    setForm({
      name: item.name,
      description: item.description,
      category: item.category,
      base_price: String(item.price ?? '0'),
      image_url: item.image_url ?? '',
      station_type: item.station_type,
      is_available: item.is_available,
      preparation_profile: item.preparation_profile,
    })
  }

  const filtered = items.filter(
    (item) =>
      !search ||
      item.name.toLowerCase().includes(search.toLowerCase()) ||
      item.category.toLowerCase().includes(search.toLowerCase()),
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-900/60 pb-3">
        <div>
          <h2 className="text-lg font-black text-white tracking-wide uppercase flex items-center gap-2">
            <Utensils className="h-5 w-5 text-brand-400" />
            Catálogo de Produtos
          </h2>
          <p className="text-xs text-gray-550 font-medium mt-0.5">
            Gerencie o portfólio de itens que a casa oferece
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setForm(EMPTY_FORM)
            setIsCreating(true)
          }}
          className="rounded-xl bg-brand-500 hover:bg-brand-600 px-4 py-2 text-xs font-bold text-white transition flex items-center gap-1.5"
        >
          <Plus className="h-4 w-4" />
          Novo Produto
        </button>
      </div>

      {/* Search */}
      <div className="relative max-w-xs">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
        <input
          type="text"
          placeholder="Buscar por nome ou categoria..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full rounded-xl pl-10 pr-4 py-3 text-xs text-white glass-input"
        />
      </div>

      {/* Loading */}
      {isLoading ? (
        <div className="h-48 rounded-2xl border border-gray-900 bg-gray-950/20 animate-pulse flex items-center justify-center text-xs text-gray-500 italic">
          Carregando catálogo...
        </div>
      ) : /* Empty state */
      items.length === 0 ? (
        <div className="border border-dashed border-gray-850 rounded-2xl p-12 text-center space-y-3">
          <p className="text-xs text-gray-500 italic">Nenhum produto cadastrado no catálogo.</p>
          <button
            type="button"
            onClick={() => {
              setForm(EMPTY_FORM)
              setIsCreating(true)
            }}
            className="mx-auto rounded-lg bg-gray-900 px-3 py-1.5 text-[10px] font-bold text-brand-400 border border-brand-500/10 hover:bg-gray-850 transition"
          >
            Criar Primeiro Produto
          </button>
        </div>
      ) : /* Items grid */
      filtered.length === 0 ? (
        <div className="border border-dashed border-gray-850 rounded-2xl p-12 text-center">
          <p className="text-xs text-gray-500 italic">
            Nenhum resultado para &ldquo;{search}&rdquo;.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((item) => (
            <div
              key={item.id}
              className="rounded-2xl border border-gray-900/60 bg-gray-950/15 p-4 space-y-3 relative group hover:border-gray-800 transition"
            >
              <div className="flex items-start gap-3">
                {item.image_url ? (
                  <img
                    src={item.image_url}
                    alt={item.name}
                    className="w-14 h-14 rounded-xl object-cover bg-gray-900 border border-gray-850"
                  />
                ) : (
                  <div className="w-14 h-14 rounded-xl bg-gray-900 border border-gray-850 flex items-center justify-center text-gray-600">
                    <Sparkles className="h-6 w-6" />
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <h4 className="text-xs font-bold text-gray-200 truncate pr-6">{item.name}</h4>
                  <p className="text-[10px] text-gray-550 mt-0.5 line-clamp-2">
                    {item.description || 'Sem descrição.'}
                  </p>
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-[9px] uppercase font-bold text-brand-400 px-1.5 py-0.5 rounded bg-brand-500/5 border border-brand-500/10">
                      {item.category}
                    </span>
                    {item.price !== null && (
                      <span className="text-[10px] font-black text-amber-500">
                        R$ {Number(item.price).toFixed(2)}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2 pt-2 border-t border-gray-900/40">
                <button
                  type="button"
                  onClick={() => handleToggleAvailability(item)}
                  className={`text-[9px] uppercase font-extrabold tracking-wider px-2 py-1 rounded-lg border transition ${
                    item.is_available
                      ? 'text-emerald-400 border-emerald-500/20 bg-emerald-950/10'
                      : 'text-gray-500 border-gray-800 bg-gray-950/40'
                  }`}
                >
                  {item.is_available ? 'Disponível' : 'Indisponível'}
                </button>

                <div className="ml-auto flex gap-1">
                  <button
                    type="button"
                    onClick={() => setRecipeItem(item)}
                    className="text-gray-600 hover:text-emerald-400 p-1 rounded transition"
                    title="Gerenciar Receita"
                  >
                    <BookOpen className="h-3.5 w-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => openEdit(item)}
                    className="text-gray-600 hover:text-brand-400 p-1 rounded transition"
                    title="Editar Produto"
                  >
                    <svg
                      className="h-3.5 w-3.5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2}
                      aria-label="Editar"
                    >
                      <title>Editar</title>
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                      />
                    </svg>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDelete(item)}
                    className="text-gray-600 hover:text-rose-500 p-1 rounded transition"
                    title="Excluir Produto"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal: Create Product */}
      {isCreating && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <form
            onSubmit={handleCreate}
            className="w-full max-w-sm rounded-2xl glass-elevated p-6 space-y-4"
          >
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                  Novo Produto
                </h3>
                <p className="text-xs text-gray-550 mt-1">Adicione um item ao catálogo</p>
              </div>
              <button
                type="button"
                onClick={() => setIsCreating(false)}
                className="text-gray-500 hover:text-white p-1"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-3">
              <div className="space-y-1.5">
                <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                  Nome do Produto
                </span>
                <input
                  type="text"
                  required
                  placeholder="Ex: Filé Mignon Grelhado"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
                />
              </div>

              <div className="space-y-1.5">
                <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                  Descrição
                </span>
                <input
                  type="text"
                  placeholder="Ex: Acompanha arroz, batatas e farofa"
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                    Categoria
                  </span>
                  <select
                    value={form.category}
                    onChange={(e) => setForm({ ...form, category: e.target.value })}
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
                    value={form.base_price}
                    onChange={(e) => setForm({ ...form, base_price: e.target.value })}
                    className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                    Perfil de Preparo
                  </span>
                  <select
                    value={form.preparation_profile}
                    onChange={(e) => setForm({ ...form, preparation_profile: e.target.value })}
                    className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input bg-[#0b0b11]"
                  >
                    <option value="STANDARD">STANDARD (Cozinha)</option>
                    <option value="NO_PREP">NO_PREP (Bebidas)</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                    Estação
                  </span>
                  <select
                    value={form.station_type}
                    onChange={(e) => setForm({ ...form, station_type: e.target.value })}
                    className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input bg-[#0b0b11]"
                  >
                    <option value="GRILL">Cozinha (GRILL)</option>
                    <option value="BEVERAGE">Copa (BEVERAGE)</option>
                  </select>
                </div>
              </div>

              <div className="space-y-1.5">
                <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                  URL da Imagem (Opcional)
                </span>
                <input
                  type="url"
                  placeholder="https://imagens.com/prato.jpg"
                  value={form.image_url}
                  onChange={(e) => setForm({ ...form, image_url: e.target.value })}
                  className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
                />
              </div>
            </div>

            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={() => setIsCreating(false)}
                className="flex-1 rounded-xl border border-gray-850 hover:bg-white/[0.02] py-2.5 text-xs font-bold text-gray-400 transition"
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="flex-1 rounded-xl bg-brand-500 hover:bg-brand-600 py-2.5 text-xs font-bold text-white transition"
              >
                Criar Produto
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Modal: Recipe Manager */}
      {recipeItem && (
        <RecipeManager
          menuItemId={recipeItem.id}
          menuItemName={recipeItem.name}
          onClose={() => setRecipeItem(null)}
        />
      )}

      {/* Modal: Edit Product */}
      {editingItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <form
            onSubmit={handleUpdate}
            className="w-full max-w-sm rounded-2xl glass-elevated p-6 space-y-4"
          >
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                  Editar Produto
                </h3>
                <p className="text-xs text-gray-550 mt-1">Atualize os dados do item</p>
              </div>
              <button
                type="button"
                onClick={() => {
                  setEditingItem(null)
                  setForm(EMPTY_FORM)
                }}
                className="text-gray-500 hover:text-white p-1"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-3">
              <div className="space-y-1.5">
                <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                  Nome do Produto
                </span>
                <input
                  type="text"
                  required
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
                />
              </div>

              <div className="space-y-1.5">
                <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                  Descrição
                </span>
                <input
                  type="text"
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                    Categoria
                  </span>
                  <select
                    value={form.category}
                    onChange={(e) => setForm({ ...form, category: e.target.value })}
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
                    value={form.base_price}
                    onChange={(e) => setForm({ ...form, base_price: e.target.value })}
                    className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                    Estação
                  </span>
                  <select
                    value={form.station_type}
                    onChange={(e) => setForm({ ...form, station_type: e.target.value })}
                    className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input bg-[#0b0b11]"
                  >
                    <option value="GRILL">Cozinha (GRILL)</option>
                    <option value="BEVERAGE">Copa (BEVERAGE)</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                    Disponibilidade
                  </span>
                  <select
                    value={form.is_available ? 'true' : 'false'}
                    onChange={(e) => setForm({ ...form, is_available: e.target.value === 'true' })}
                    className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input bg-[#0b0b11]"
                  >
                    <option value="true">Disponível</option>
                    <option value="false">Indisponível</option>
                  </select>
                </div>
              </div>

              <div className="space-y-1.5">
                <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                  URL da Imagem
                </span>
                <input
                  type="url"
                  value={form.image_url}
                  onChange={(e) => setForm({ ...form, image_url: e.target.value })}
                  className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
                />
              </div>
            </div>

            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={() => {
                  setEditingItem(null)
                  setForm(EMPTY_FORM)
                }}
                className="flex-1 rounded-xl border border-gray-850 hover:bg-white/[0.02] py-2.5 text-xs font-bold text-gray-400 transition"
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="flex-1 rounded-xl bg-brand-500 hover:bg-brand-600 py-2.5 text-xs font-bold text-white transition"
              >
                Salvar
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
