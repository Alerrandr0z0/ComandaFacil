import { AlertTriangle, Minus, Plus, Sparkles, Utensils } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { httpClient } from '@/shared/lib/http_client'

interface StockItem {
  id: number
  name: string
  category: string
  current_quantity_amount: number
  current_quantity_unit: string
  is_low_stock: boolean
}

interface RecipeIngredient {
  stock_item_id: number
  quantity_value: number
  quantity_unit: string
}

interface Recipe {
  menu_item_id: number
  ingredients: RecipeIngredient[]
}

interface RecipeManagerProps {
  menuItemId: number
  menuItemName: string
  onClose: () => void
}

export default function RecipeManager({ menuItemId, menuItemName, onClose }: RecipeManagerProps) {
  const [stockItems, setStockItems] = useState<StockItem[]>([])
  const [ingredients, setIngredients] = useState<RecipeIngredient[]>([])
  const [savedRecipe, setSavedRecipe] = useState<Recipe | null>(null)
  const [isLoadingStock, setIsLoadingStock] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const searchRef = useRef<HTMLInputElement>(null)

  const fetchStock = useCallback(async () => {
    try {
      const res = await httpClient.get<StockItem[]>('/v1/stock/items')
      setStockItems(res.data)
    } catch {
      setError('Falha ao carregar itens de estoque.')
    } finally {
      setIsLoadingStock(false)
    }
  }, [])

  const fetchRecipe = useCallback(async () => {
    try {
      const res = await httpClient.get<Recipe>(`/v1/stock/recipes/${menuItemId}`)
      setSavedRecipe(res.data)
      setIngredients(res.data.ingredients)
    } catch {
      setSavedRecipe(null)
      setIngredients([])
    }
  }, [menuItemId])

  useEffect(() => {
    fetchStock()
    fetchRecipe()
  }, [fetchStock, fetchRecipe])

  const addIngredient = (stockItem: StockItem) => {
    if (ingredients.some((i) => i.stock_item_id === stockItem.id)) return
    setIngredients((prev) => [
      ...prev,
      {
        stock_item_id: stockItem.id,
        quantity_value: 1,
        quantity_unit: stockItem.current_quantity_unit,
      },
    ])
    setSearchQuery('')
    searchRef.current?.focus()
  }

  const removeIngredient = (stockItemId: number) => {
    setIngredients((prev) => prev.filter((i) => i.stock_item_id !== stockItemId))
  }

  const updateQuantity = (stockItemId: number, value: number) => {
    setIngredients((prev) =>
      prev.map((i) =>
        i.stock_item_id === stockItemId ? { ...i, quantity_value: Math.max(0.1, value) } : i,
      ),
    )
  }

  const handleSave = async () => {
    if (ingredients.length === 0) return
    setIsSaving(true)
    setError(null)
    try {
      await httpClient.put(`/v1/stock/recipes/${menuItemId}`, { ingredients })
      setSavedRecipe({ menu_item_id: menuItemId, ingredients })
      setSuccessMessage('✅ Receita salva com sucesso!')
    } catch {
      setError('Falha ao salvar receita.')
    } finally {
      setIsSaving(false)
    }
  }

  const filteredStock = stockItems.filter(
    (s) =>
      s.name.toLowerCase().includes(searchQuery.toLowerCase()) &&
      !ingredients.some((i) => i.stock_item_id === s.id),
  )

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-lg rounded-2xl glass-elevated p-6 space-y-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Utensils className="h-4 w-4 text-brand-400" />
              Receita: {menuItemName}
            </h3>
            <p className="text-[10px] text-gray-500 font-medium mt-0.5">
              Vincule ingredientes do estoque a este item do cardápio
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-gray-800 hover:bg-white/[0.03] px-3 py-1.5 text-[10px] font-bold text-gray-400 transition"
          >
            Fechar
          </button>
        </div>

        {error && (
          <div className="flex items-center gap-2 rounded-xl border border-rose-900/40 bg-rose-950/10 p-3 text-[10px] text-rose-400">
            <AlertTriangle className="h-4 w-4 flex-shrink-0" />
            {error}
          </div>
        )}

        {successMessage && (
          <div className="rounded-xl border border-emerald-900/40 bg-emerald-950/10 p-3 text-[10px] text-emerald-400">
            {successMessage}
          </div>
        )}

        <div className="space-y-3">
          <h4 className="text-[10px] font-extrabold uppercase tracking-wider text-gray-500">
            Ingredientes ({ingredients.length})
          </h4>

          {ingredients.length === 0 ? (
            <div className="border border-dashed border-gray-850 rounded-xl p-6 text-center">
              <Sparkles className="h-6 w-6 text-gray-600 mx-auto mb-2" />
              <p className="text-[10px] text-gray-500 italic">Nenhum ingrediente vinculado.</p>
              <p className="text-[9px] text-gray-600 mt-1">
                Use o campo abaixo para adicionar insumos do estoque.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {ingredients.map((ing) => {
                const stock = stockItems.find((s) => s.id === ing.stock_item_id)
                return (
                  <div
                    key={ing.stock_item_id}
                    className="flex items-center gap-3 p-3 rounded-xl border border-gray-900/60 bg-gray-950/20"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-bold text-gray-200 truncate">
                          {stock?.name || `#${ing.stock_item_id}`}
                        </span>
                        {stock?.is_low_stock && (
                          <AlertTriangle className="h-3 w-3 text-rose-400 flex-shrink-0" />
                        )}
                      </div>
                      {stock && (
                        <span className="text-[9px] text-gray-500">
                          Estoque: {stock.current_quantity_amount} {stock.current_quantity_unit}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-1">
                      <input
                        type="number"
                        step="0.1"
                        min="0.1"
                        value={ing.quantity_value}
                        onChange={(e) =>
                          updateQuantity(ing.stock_item_id, parseFloat(e.target.value) || 0.1)
                        }
                        className="w-16 rounded-lg bg-gray-900 border border-gray-800 px-2 py-1 text-[10px] text-white text-center"
                      />
                      <span className="text-[10px] text-gray-400 w-8">{ing.quantity_unit}</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => removeIngredient(ing.stock_item_id)}
                      className="rounded-lg bg-rose-500/10 border border-rose-500/20 hover:bg-rose-500/20 p-1.5 transition"
                    >
                      <Minus className="h-3 w-3 text-rose-400" />
                    </button>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        <div className="space-y-2">
          <h4 className="text-[10px] font-extrabold uppercase tracking-wider text-gray-500">
            Adicionar Insumo
          </h4>
          <div className="relative">
            <input
              ref={searchRef}
              type="text"
              placeholder="Buscar insumo no estoque..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
            />
            {searchQuery && filteredStock.length > 0 && (
              <div className="absolute z-10 mt-1 w-full rounded-xl border border-gray-800 bg-gray-950 shadow-xl max-h-48 overflow-y-auto">
                {filteredStock.map((s) => (
                  <button
                    type="button"
                    key={s.id}
                    onClick={() => addIngredient(s)}
                    className="flex items-center justify-between w-full px-4 py-2.5 text-xs text-gray-300 hover:bg-white/[0.03] transition text-left"
                  >
                    <div className="flex items-center gap-2">
                      <span>{s.name}</span>
                      {s.is_low_stock && <AlertTriangle className="h-3 w-3 text-rose-400" />}
                    </div>
                    <span className="text-[9px] text-gray-500">
                      {s.current_quantity_amount} {s.current_quantity_unit}
                    </span>
                  </button>
                ))}
              </div>
            )}
            {searchQuery && filteredStock.length === 0 && !isLoadingStock && (
              <div className="absolute z-10 mt-1 w-full rounded-xl border border-gray-800 bg-gray-950 p-3 text-center text-[10px] text-gray-500 italic">
                Nenhum insumo encontrado.
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center justify-end border-t border-gray-900 pt-4">
          <button
            type="button"
            onClick={handleSave}
            disabled={isSaving || ingredients.length === 0}
            className="rounded-lg bg-emerald-500 hover:bg-emerald-600 disabled:opacity-40 px-3 py-1.5 text-[10px] font-bold text-white transition flex items-center gap-1"
          >
            <Plus className="h-3 w-3" />
            {isSaving ? 'Salvando...' : savedRecipe ? 'Atualizar Receita' : 'Salvar Receita'}
          </button>
        </div>
      </div>
    </div>
  )
}
